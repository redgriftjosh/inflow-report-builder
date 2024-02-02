import json
import sys
import common_functions
import time

def get_payload():
    data = json.loads(sys.argv[1])

    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    return dev, report_id

def get_drains(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    
    try:
        return report_json["response"]["drain"]
    except:
        print(f"Can't find any drains...?", "is_loading_error", file=sys.stderr)
        sys.exit(1)

def get_kw_per_year(drain, peak_acfm_15_min, kw_max_avg_15, dev):
    drain_json = common_functions.get_req("drain", drain, dev)
    try:
        acfm_loss = drain_json["response"]["acfm_loss"]
    except:
        acfm_loss = 0

    return acfm_loss * kw_max_avg_15 / peak_acfm_15_min

def get_global_values(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    try:
        peak_acfm_15_min = report_json["response"]["15 Min Peak Flow"]
        kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]

    except:
        print(f"I need Peak 15 Minute kW and ACFM from table 3.2... Did you already run that?", file=sys.stderr)
        sys.exit(1)
    
    hours_annual = common_functions.get_total_annual_operating_hours(report_json, dev)

    return peak_acfm_15_min, kw_max_avg_15, hours_annual
    



def start():
    # Grab the variabls from the json payload
    dev, report_id = get_payload()

    # We need 15 minute peak acfm and 15 minute peak kw
    peak_acfm_15_min, kw_max_avg_15, hours_annual = get_global_values(report_id, dev)

    # Get array of drain IDs
    drains = get_drains(report_id, dev)

    #loop through each drain to start calculations
    for drain in drains:
        kw_per_year = get_kw_per_year(drain, peak_acfm_15_min, kw_max_avg_15, dev)

        kwh_annual = kw_per_year * hours_annual

        common_functions.get_cost_to_operate(report_id, kw_max_avg_15, kwh_annual,)


start()