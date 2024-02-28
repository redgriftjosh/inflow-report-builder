import sys
import json
import os

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

def get_baseline_total_cost(scenario_json, dev):
    scenario_baseline_id = scenario_json["response"]["scenario_baseline"]
    scenario_baseline_json = common_functions.get_req("scenario_baseline", scenario_baseline_id, dev)
    baseline_operation_7_1 = scenario_baseline_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    total_cost_to_operate = []
    for baseline_operation_7_1_row in baseline_operation_7_1_rows:
        baseline_operation_7_1_row_json = common_functions.get_req("baseline_operation_7_1_row", baseline_operation_7_1_row, dev)
        cost_to_operate = baseline_operation_7_1_row_json["response"]["cost_to_operate"]
        total_cost_to_operate.append(cost_to_operate)
    
    return sum(total_cost_to_operate)

def get_proposed_total_cost(scenario_json, dev):
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    proposed_operation_7_1 = scenario_proposed_json["response"]["baseline_operation_7_1"]
    proposed_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", proposed_operation_7_1, dev)
    proposed_operation_7_1_rows = proposed_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    total_cost_to_operate = []
    for proposed_operation_7_1_row in proposed_operation_7_1_rows:
        proposed_operation_7_1_row_json = common_functions.get_req("baseline_operation_7_1_row", proposed_operation_7_1_row, dev)
        cost_to_operate = proposed_operation_7_1_row_json["response"]["cost_to_operate"]
        total_cost_to_operate.append(cost_to_operate)
    
    return sum(total_cost_to_operate)

def get_proposed_things(scenario_json, report_id, dev):
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    proposed_operation_7_1 = scenario_proposed_json["response"]["baseline_operation_7_1"]
    proposed_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", proposed_operation_7_1, dev)
    proposed_operation_7_1_rows = proposed_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    report_json = common_functions.get_req("report", report_id, dev)
    total_hours = report_json["response"]["total_hours"]

    total_kwh_annuals = []
    total_cost_kws = []
    kw_demand_15mins = []
    for proposed_operation_7_1_row in proposed_operation_7_1_rows:
        proposed_operation_7_1_row_json = common_functions.get_req("baseline_operation_7_1_row", proposed_operation_7_1_row, dev)
        average_kw_demand = proposed_operation_7_1_row_json["response"]["average_kw_demand"]
        kwh_annual = proposed_operation_7_1_row_json["response"]["kwh_annual"]
        kw_demand_15min = proposed_operation_7_1_row_json["response"]["kw_demand_15min"]

        kw_demand_15mins.append(kw_demand_15min)
        total_cost_kws.append(average_kw_demand)
        total_kwh_annuals.append(kwh_annual)
    
    avg_kws = sum(total_kwh_annuals) / total_hours

    total_kwh_annual = sum(total_kwh_annuals)
    return avg_kws, total_kwh_annual, sum(kw_demand_15mins)

def get_baseline_things(scenario_json, report_id, dev):
    scenario_baseline_id = scenario_json["response"]["scenario_baseline"]
    scenario_baseline_json = common_functions.get_req("scenario_baseline", scenario_baseline_id, dev)
    baseline_operation_7_1 = scenario_baseline_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    report_json = common_functions.get_req("report", report_id, dev)
    total_hours = report_json["response"]["total_hours"]

    total_cost_kws = []
    total_kwh_annuals = []
    kw_demand_15mins = []
    for baseline_operation_7_1_row in baseline_operation_7_1_rows:
        baseline_operation_7_1_row_json = common_functions.get_req("baseline_operation_7_1_row", baseline_operation_7_1_row, dev)
        average_kw_demand = baseline_operation_7_1_row_json["response"]["average_kw_demand"]
        kwh_annual = baseline_operation_7_1_row_json["response"]["kwh_annual"]
        kw_demand_15min = baseline_operation_7_1_row_json["response"]["kw_demand_15min"]

        kw_demand_15mins.append(kw_demand_15min)
        total_cost_kws.append(average_kw_demand)
        total_kwh_annuals.append(kwh_annual)
    
    avg_kws = sum(total_kwh_annuals) / total_hours

    total_kwh_annual = sum(total_kwh_annuals)
    return avg_kws, total_kwh_annual, sum(kw_demand_15mins)

def start():
    dev, report_id, scenario_id = get_payload()

    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    proposed_cost_to_operate = get_proposed_total_cost(scenario_json, dev)
    baseline_cost_to_operate = get_baseline_total_cost(scenario_json, dev)

    proposed_avg_kw, proposed_kwh_annual, proposed_kw_demand_15min = get_proposed_things(scenario_json, report_id, dev)
    baseline_avg_kw, baseline_kwh_annual, baseline_kw_demand_15min = get_baseline_things(scenario_json, report_id, dev)

    kw_demand = baseline_avg_kw - proposed_avg_kw

    kw_max = baseline_kw_demand_15min - proposed_kw_demand_15min

    dollars_per_yr = baseline_cost_to_operate - proposed_cost_to_operate

    total_kwh_annual = baseline_kwh_annual - proposed_kwh_annual

    scenario_end_values = scenario_json["response"]["scenario_end_values"]

    common_functions.patch_req("scenario_end_values", scenario_end_values, body = {
        "dollars_per_yr": dollars_per_yr,
        "kw_demand": kw_demand,
        "kw_max": kw_max,
        "kwh_annual": total_kwh_annual
        }, dev=dev)


start()