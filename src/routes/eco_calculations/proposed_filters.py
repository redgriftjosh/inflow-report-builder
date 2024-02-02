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
    response = common_functions.post_req("scenario_differences", body={"operation_period": op_id}, dev=dev)

    scenario_difference = response["id"]

    common_functions.patch_req("operation_period", op_id, body={"scenario_differences": scenario_difference}, dev=dev)

    return scenario_difference

def get_total_report_filter_psi_drop(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    filter_ids = report_json["response"]["filter"]

    psi_drops = []
    for filter_id in filter_ids:
        filter_json = common_functions.get_req("filter", filter_id, dev)
        psi_drop = filter_json["response"]["psig_drop"]

        psi_drops.append(psi_drop)

    total_psi_drop = sum(psi_drops)

    return total_psi_drop

def get_total_proposed_filter_psi_drop(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    filter_ids = scenario_proposed_json["response"]["filter"]

    psi_drops = []
    for filter_id in filter_ids:
        filter_json = common_functions.get_req("filter", filter_id, dev)
        psi_drop = filter_json["response"]["psig_drop"]

        psi_drops.append(psi_drop)
    
    total_proposed_filter_psi_drop = sum(psi_drops)

    return total_proposed_filter_psi_drop

def get_op_ids(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)

    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    operating_period_ids = scenario_proposed_json["response"]["operation_period"]

    return operating_period_ids

def start():
    dev, report_id, scenario_id = get_payload()
    
    total_proposed_filter_psi_drop = get_total_proposed_filter_psi_drop(scenario_id, dev)
    total_report_filter_psi_drop = get_total_report_filter_psi_drop(report_id, dev)

    total_filter_psi_drop = total_proposed_filter_psi_drop - total_report_filter_psi_drop

    operating_period_ids = get_op_ids(scenario_id, dev)

    for operating_period_id in operating_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        try:
            scenario_differences = operating_period_json["response"]["scenario_differences"]
        except:
            scenario_differences = create_new_scenario_difference(operating_period_id, dev)

        common_functions.patch_req("scenario_differences", scenario_differences, body={"filter_psi_change": total_filter_psi_drop}, dev=dev)

        proposed_global.update_op_stats(operating_period_id, report_id, dev)


start()
