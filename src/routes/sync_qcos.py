

import json
import sys

from utilities import requests_util


def get_payload():
    data = json.loads(sys.argv[1])

    try:
        dev = data["dev"]
        if dev == 'yes':
            dev = '/version-test'
        else:
            dev = ''
    except:
        print(f"Can't find variable: dev", file=sys.stderr)
        sys.exit(1)
    
    try:
        report_id = data["report_id"]
    except:
        print(f"Can't find variable: report_id", file=sys.stderr)
        sys.exit(1)

    try:
        user_id = data["user_id"]
    except:
        print(f"Can't find variable: user_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, user_id

def delete_report_qcos(report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    qcos_id = report_json["response"]["qcos"]
    qcos_json = requests_util.get_req("qcos", qcos_id, dev)
    page_ids = qcos_json["response"]["page"]

    for page_id in page_ids:
        page_json = requests_util.get_req("page", page_id, dev)
        qco_ids = page_json["response"]["qco"]

        for qco_id in qco_ids:
            requests_util.del_req("qco", qco_id, dev)

        requests_util.del_req("page", page_id, dev)

    return qcos_id

def copy_user_qcos(report_id, user_id, dev, r_qcos_id):

    user_json = requests_util.get_req("User", user_id, dev)
    qcos = user_json["response"]["qcos"]

    qcos_json = requests_util.get_req("qcos", qcos, dev)
    page_ids = qcos_json["response"]["page"]

    r_page_ids = []
    i = 1
    for page_id in page_ids:
        page_json = requests_util.get_req("page", page_id, dev)
        print(f"page_json: {page_json}")
        qco_ids = page_json["response"]["qco"]

        r_qco_ids = []
        for qco_id in qco_ids:
            qco_json = requests_util.get_req("qco", qco_id, dev)
            print(f"qco_json: {qco_json}")
            response = qco_json["response"]

            requests_util.patch_req("Report", report_id, body={"loading": f"Page: {i}, {response.get('num', '')}", "is_loading_error": "no"}, dev=dev)

            body = {
                "num": response.get("num", ""),
                "header": response.get("header", ""),
                "subheader": response.get("subheader", ""),
                "small_body": response.get("small_body", ""),
                "note": response.get("note", ""),
                "category": response.get("category", "")
            }
            post_response = requests_util.post_req("qco", body, dev)
            r_qco_ids.append(post_response["id"])

        page_response = requests_util.post_req("page", body={"qco": r_qco_ids}, dev=dev)
        r_page_ids.append(page_response["id"])
        i += 1
    
    requests_util.patch_req("qcos", r_qcos_id, body={"page": r_page_ids}, dev=dev)

def start():
    dev, report_id, user_id = get_payload()

    qcos_id = delete_report_qcos(report_id, dev)
    copy_user_qcos(report_id, user_id, dev, qcos_id)



start()