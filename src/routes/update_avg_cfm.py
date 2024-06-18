import json, sys
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

    return dev, report_id

def get_op_values(report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    operation_ids = report_json["response"]["operation_period"]
    op_hours = []
    op_acfms = []
    for operation_id in operation_ids:
        operation_json = requests_util.get_req("operation_period", operation_id, dev)
        op_hours.append(operation_json["response"]["Hours/yr"])
        op_acfms.append(operation_json["response"]["ACFM Made"])
    return op_hours, op_acfms

def update_avg_acfm(avg_acfm, report_id, dev):
    requests_util.patch_req("report", report_id, {"avg_acfm": avg_acfm}, dev)

def start():
    dev, report_id = get_payload()
    print(f"report_id: {report_id}, dev: {dev}")
    op_hours, op_acfm = get_op_values(report_id, dev)

    avg_acfm_per_op = []
    total_hours = 0
    for i in range(len(op_hours)):
        avg_acfm_per_op.append(op_hours[i] * op_acfm[i])
        total_hours += op_hours[i]

    new_acfm = 0

    for acfm in avg_acfm_per_op:
        new_acfm += acfm

    total_avg_acfm = new_acfm / total_hours

    update_avg_acfm(total_avg_acfm, report_id, dev)

start()