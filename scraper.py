import requests
from bs4 import BeautifulSoup as BS
import json
from log import log
from time import sleep
import random

def get_proxy(proxy_list):
    '''
    (list) -> dict
    Given a proxy list <proxy_list>, a proxy is selected and returned.
    '''
    # Choose a random proxy
    proxy = random.choice(proxy_list)

    # Set up the proxy to be used
    proxies = {
        "http": "http://" + str(proxy),
        "https": "https://" + str(proxy)
    }

    # Return the proxy
    return proxies

class NYCScraper():
    def __init__(self, id, proxies=[]):
        super().__init__()

        self.session = requests.session()
        self.id = id
        self.proxies = proxies
        self.url = "http://a810-bisweb.nyc.gov/bisweb/LicenseQueryServlet"
        self.params = {
            "licensetype": "G",
            "licno" : self.id,
            "requestid" : "1"
        }
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3",
            'Accept-Language': 'en-US,en;q=0.9',
            "Accept-Encoding": "gzip, deflate, br",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.130 Safari/537.36"
        }
        self.data = {
                "Name": "",
                "RegStatus": "",
                "Date" : "",
                "ContractorID": "",
                "Expiration": "",
                "Status": "",
                "Business Phone": "",
                "City employee": "",
                "OfficeAddress": "",
                "Business 1": "",
                "Insurance": [],
                "Endorsements": []
            }

    def run(self):
        i = 0
        while True:
            i += 1
            if len(self.proxies):
                proxies = get_proxy(self.proxies)
            else:
                proxies = None
            try:
                response = self.session.get(self.url, headers=self.headers, proxies=proxies, params=self.params, timeout=10)
                break
            except Exception as e:
                if i == 20:
                    return {
                        "success" : False,
                        "licenseID" : self.id,
                        "message" : {
                            "errorText" :  "Connection Error : {}".format(repr(e))
                        }
                    }
                continue
        if response.status_code == 200:
            return self.get_json(response)
        else:
            return {
                "success" : False,
                "licenseID" : self.id,
                "message" : {
                    "errorText" :  "Access Denied {}".format(response.status_code)
                }
            }

    def get_json(self, response):

        name = ""
        date = ""
        reg_status = ""
        city_employee = ""
        contractor_id = ""
        expiration = ""
        status = ""
        office_address = ""
        businees_phone = ""
        business_1 = ""

        soup = BS(response.content, 'lxml')
        lower_text = response.text.lower()
        if "license record not found" in lower_text:
            return {
                "success" : True,
                "licenseID" : self.id,
                "is_data_exist" : False,
                "message" : {
                    "text" : "LICENSE RECORD NOT FOUND"
                }
            }
        elif "your request is being processed" in lower_text:
            return {
                "success" : False,
                "licenseID" : self.id,
                "message" : {
                    "errorText" : "Your request is being processed, Due to the high demand it may take a little longer. Please retry after a few minutes"
                }
            }
        elif "you don't have permission to access" in lower_text:
            return {
                "success" : False,
                "licenseID" : self.id,
                "message" : {
                    "errorText" : "You don't have permission to access on this server"
                }
            }

        try:
            table_soup = soup.find('table', {"width" : "750"})
            data_rows = table_soup.find_all('tr', recursive=False)
            if data_rows[0].text.lower() in "non-registered":
                reg_status ="non-registered"
            else:
                reg_status = "registered"
        except Exception as e:
            with open("error.html", 'wb') as f:
                f.write(response.content)
            log('w', "Find RegStatus in {} : ".format(self.id) +  repr(e)) 

        try:
            details_table = table_soup.find_all('table')[0]
            details = details_table.find_all('td', "content")
            for td in details:
                try:
                    row_data = td.text.strip()
                    if "date" in row_data.lower():
                        date = row_data.split(":")[1].strip()
                    elif "employee" in row_data.lower():
                        city_employee = row_data.split(":")[1].strip()
                    elif "contractor" in row_data.lower():
                        contractor_id = int(row_data.split(":")[1].strip())
                    elif "expiration" in row_data.lower():
                        expiration = row_data.split(":")[1].strip()
                    elif "status" in row_data.lower():
                        status = row_data.split(":")[1].strip()
                    elif "office" in row_data.lower():
                        office_address = row_data.split(":")[1].strip()
                        office_address = " ".join(office_address.split())
                    elif "phone" in row_data.lower():
                        businees_phone = row_data.split(":")[1].strip()
                except Exception as e:
                    log('w', "Find Insurance in {} : ".format(self.id) + repr(e))
                    continue
        except Exception as e:
            log('w', "Find Detail in {} : ".format(self.id) +  repr(e)) 

        try:
            name = details_table.parent.parent.find_previous_sibling('tr').text.strip()
            name = " ".join(name.split())
        except Exception as e:
            log('w', "Find Name in {} : ".format(self.id) + repr(e)) 

        try:
            insurence = table_soup.find_all('table')[2]
            try:
                for td in insurence.find_all('td', 'content'):
                    td_text = td.text.strip()
                    if "business 1" in td_text.lower():
                        business_1 = td_text.split(":")[1].strip()
                        break
            except Exception as e:
                log('w', "Find Business 1 in {} : ".format(self.id) + repr(e)) 

            general_liability = insurence.find(text="General Liability").parent.parent.parent
            gl_contents = general_liability.find_all('td', 'centercontent')
            gl = {
                "type" : "GL",
                "policy" : gl_contents[0].string,
                "required" : gl_contents[1].string,
                "Company" : gl_contents[2].string,
                "ExpirationDate" : gl_contents[3].string
            }
            workers_compensation = insurence.find(text="Workers' Compensation").parent.parent.parent
            wc_contents = workers_compensation.find_all('td', 'centercontent')
            wc = {
                "type" : "WC",
                "policy" : wc_contents[0].string,
                "required" : wc_contents[1].string,
                "Company" : wc_contents[2].string,
                "ExpirationDate" : wc_contents[3].string
            }
            disability = insurence.find(text="Disability").parent.parent.parent
            di_contents = disability.find_all('td', 'centercontent')
            di = {
                "type" : "DI",
                "policy" : di_contents[0].string,
                "required" : di_contents[1].string,
                "Company" : di_contents[2].string,
                "ExpirationDate" : di_contents[3].string
            }
        except Exception as e:
            log('w', "Find Insurance in {} : ".format(self.id) + repr(e)) 

        try:
            self.data.update({'Name' : name})
            self.data.update({'RegStatus' : reg_status})
            self.data.update({"Date" : date})
            self.data.update({'ContractorID': contractor_id})
            self.data.update({'Expiration' : expiration})
            self.data.update({"City employee" : city_employee})
            self.data.update({"OfficeAddress" : office_address})
            self.data.update({"Status": status})
            self.data.update({"Business Phone": businees_phone})
            self.data.update({"Business 1": business_1})
            self.data.get('Insurance').append(gl)
            self.data.get('Insurance').append(wc)
            self.data.get('Insurance').append(di)
        except Exception as e:
            log('w', "Find Insurance in {} :".format(self.id) + repr(e))

        try:
            for endorsement in table_soup.find(text="Endorsements").parent.parent.find_next_siblings('tr'):
                endor_txt = endorsement.text.strip()
                if "none" in endor_txt.lower():
                    break
                endor_status = endor_txt.split('Type:')[0].split(":")[1].strip()
                endor_type = " ".join(endor_txt.split('Type:')[1].strip().split())
                self.data.get('Endorsements').append({
                    "Status" : endor_status,
                    "Type" : endor_type
                })
        except Exception as e:
            log('w', "Find Endorsements in {} : ".format(self.id) + repr(e)) 

        return {
            "success" : True,
            "licenseID" : self.id,
            "is_data_exist": True,
            "message" : self.data
        }

def read_from_txt(filename):
    raw_lines = []
    lines = []
    path = filename
    try:
        f = open(path, "r")
        raw_lines = f.readlines()
        f.close()
    except:
        return []
    for line in raw_lines:
        list = line.strip()
        if list != "":
            lines.append(list)
    return lines

if __name__ == "__main__":
    ids = read_from_txt('ids.txt')
    proxies = read_from_txt("proxies.txt")
    for id in ids:
        nycscraper = NYCScraper(id, proxies=proxies)
        json = nycscraper.run()
        sleep(3)
        print(json)