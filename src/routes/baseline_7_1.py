import sys
import json
import common_functions
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from utilities import data_crunch_util, financial_util, compressor_util, requests_util, baseline_proposed_7_1_util, pressure_util

# Make sure we have everything we need before running
def check_dependencies(report_id, report_json, dev):
    requests_util.patch_req("Report", report_id, body={"loading": f"Checking Dependencies...", "is_loading_error": "no"}, dev=dev)

    # Checking if we have at least one operation period
    try:
        operation_period_ids = report_json["response"]["operation_period"]
    except:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)


    # Checking if we have electrical utility providers entered
    try:
        electrical_provider = report_json["response"]["electrical_provider"]

        electrical_provider_json = requests_util.get_req("electrical_provider", electrical_provider, dev)
        on_peak_start = electrical_provider_json["response"]["on_peak_start"]
        off_peak_start = electrical_provider_json["response"]["off_peak_start"]

        electrical_provider_entrys = electrical_provider_json["response"]["electrical_provider_entry"]

    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = requests_util.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    demand_schedule_id = baseline_operation_7_1_json["response"]["demand_schedule_id"]

    
    return on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id
    
def create_first_baseline_operation_7_1(report_id, dev):
    response = requests_util.post_req("baseline_operation_7_1", body={"report": report_id}, dev=dev)
    baseline_operation_7_1 = response["id"]

    requests_util.patch_req("report", report_id, body={"baseline_operation_7_1": baseline_operation_7_1}, dev=dev)
    
    return baseline_operation_7_1

def reset_rows(report_id, report_json, dev):
    requests_util.patch_req("Report", report_id, body={"loading": f"Resetting Any Existing Data...", "is_loading_error": "no"}, dev=dev)

    try:
        baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]

    except:
        baseline_operation_7_1 = create_first_baseline_operation_7_1(report_id, dev)
    
    # Deleting any rows if they exist
    baseline_operation_7_1_json = requests_util.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    try:
        baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

        for row in baseline_operation_7_1_rows:
            requests_util.del_req("baseline_operation_7_1_row", row, dev)
    except:
        print(f"No Rows Found, I guess")

    requests_util.patch_req("Report", report_id, body={"loading": f"Getting started on the Calculations...", "is_loading_error": "no"}, dev=dev)

    return baseline_operation_7_1

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    # local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    report_json = requests_util.get_req("Report", report_id, dev)

    # Make sure we have everything we need before running
    on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id = check_dependencies(report_id, report_json, dev)

    # Delete any existing rows
    baseline_operation_7_1 = reset_rows(report_id, report_json, dev)

    # Run Calculations for each Operation Period
    baseline_proposed_7_1_util.start_calculations(operation_period_ids, demand_schedule_id, report_json, baseline_operation_7_1, dev)



start()


