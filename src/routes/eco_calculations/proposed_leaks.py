import os
import sys
import json
import proposed_global

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions

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
        scenario_id = data["scenario_id"]
    except:
        print(f"Can't find variable: scenario_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, scenario_id

def create_new_scenario_difference(op_id, dev):
    response = common_functions.post_req("scenario_differences", body={
        "operation_period": op_id, 
        "compressor_kw_change": 0,
        "dryer_kw_change": 0,
        "drain_cfm_change": 0,
        "dryer_cfm_change": 0,
        "filter_psi_change": 0,
        "leak_cfm_change": 0
        }, dev=dev)

    scenario_difference = response["id"]

    common_functions.patch_req("operation_period", op_id, body={"scenario_differences": scenario_difference}, dev=dev)

    return scenario_difference

def get_total_report_leak_cfm(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    leak_id = report_json["response"]["leak"]

    leak_json = common_functions.get_req("leak", leak_id, dev)

    leak_entry_ids = leak_json["response"]["leak_entry"]

    adjusted_cfms = []
    for entry in leak_entry_ids:
        leak_entry_json = common_functions.get_req("leak_entry", entry, dev)
        fixed = leak_entry_json["response"]["fixed"]
        print(f"fixed - report: {fixed}")

        if fixed == False:
            adjusted_cfm = leak_entry_json["response"]["adjusted_cfm"]

            adjusted_cfms.append(adjusted_cfm)
    
    total_report_leak_cfm = sum(adjusted_cfms)

    return total_report_leak_cfm

def get_total_proposed_leak_cfm(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    leak_id = scenario_proposed_json["response"]["leak"]

    leak_json = common_functions.get_req("leak", leak_id, dev)

    leak_entry_ids = leak_json["response"]["leak_entry"]

    adjusted_cfms = []
    for entry in leak_entry_ids:
        leak_entry_json = common_functions.get_req("leak_entry", entry, dev)
        fixed = leak_entry_json["response"]["fixed"]
        print(f"fixed - proposed: {fixed}")

        if fixed == False:
            adjusted_cfm = leak_entry_json["response"]["adjusted_cfm"]

            adjusted_cfms.append(adjusted_cfm)
    
    total_proposed_leak_cfm = sum(adjusted_cfms)

    return total_proposed_leak_cfm

def get_op_ids(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)

    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    operating_period_ids = scenario_proposed_json["response"]["operation_period"]

    return operating_period_ids

def start():
    dev, report_id, scenario_id = get_payload()
    
    total_proposed_leak_cfm = get_total_proposed_leak_cfm(scenario_id, dev)
    print(f"total_proposed_leak_cfm: {total_proposed_leak_cfm}")

    total_report_leak_cfm = get_total_report_leak_cfm(report_id, dev)
    print(f"total_report_leak_cfm: {total_report_leak_cfm}")

    total_leak_cfm = total_proposed_leak_cfm - total_report_leak_cfm
    print(f"total_leak_cfm: {total_leak_cfm}")

    operating_period_ids = get_op_ids(scenario_id, dev)

    for operating_period_id in operating_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        try:
            scenario_differences = operating_period_json["response"]["scenario_differences"]
        except:
            scenario_differences = create_new_scenario_difference(operating_period_id, dev)

        common_functions.patch_req("scenario_differences", scenario_differences, body={"leak_cfm_change": total_leak_cfm}, dev=dev)

        proposed_global.update_op_stats(operating_period_id, report_id, dev)


start()
