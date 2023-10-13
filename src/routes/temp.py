import sys
import json
import requests
import common_functions
import pandas as pd

def start():
    # data = json.loads(sys.argv[1]) # Proper Code. Keep this
    local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    data = json.loads(local_data)
    print(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    report_id = data.get('report-id')
    report_json = common_functions.get_req("Report", report_id, dev)

    trim_id = report_json["response"]["trim"]
    trim_json = common_functions.get_req("trim", trim_id, dev)

    print(report_json)


def test_sanitize():
    print(common_functions.sanitize_filename("This Is my file name"))

test_sanitize()