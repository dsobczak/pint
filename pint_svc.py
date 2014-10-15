#!/usr/bin/python

from flask import Flask, request

import os
import sys

OUTFILENAME = 'output'
TOKEN = '2Ff40CE7GILrWayppkW6Ybs5TgIaCh1m'

#
# REST SERVICE HANDLER
#

app = Flask(__name__)

@app.route('/pinterest', methods=['POST'])
def index():
    url = request.form['url']
    token = request.form['token']

    if token != TOKEN:
        return ''

    if 'pinterest' not in url:
        return ''

    os.system('python pinterest.py {}'.format(url))

    # Create JSON output
    with open(OUTFILENAME, 'rb') as outfile:
        return "[{}]".format(','.join([line.strip() for line in outfile]))

if __name__ == '__main__':
    app.run(host='0.0.0.0')
