from flask import Flask, render_template, request
from threading import Thread
from sys import argv
import logging, time, sys
from scraper import NYCScraper

logging.getLogger('werkzeug').setLevel(logging.ERROR)


app = Flask(__name__)

@app.route('/v1/json', methods=['POST'])
def json():
    id = request.get_json()['id']
    proxies = read_from_txt("proxies.txt")
    try:
        data = NYCScraper(id, proxies=proxies).run()
        return {
            "data" : data
        }, 200
    except:
        return  {
            "data" : "Server Error"
        }, 500

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
    # app.run(port=8000)
    Thread(target = lambda: app.run(host = '0.0.0.0', port=8000)).start()

