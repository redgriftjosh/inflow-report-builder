import os
import sys
import json
import baseline_global
import pandas as pd

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

def get_pressure_index(report_id, op_json, dev):
    report_json = common_functions.get_req("Report", report_id, dev)
    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)

    try:
        p_what = baseline_operation_7_1_json["response"]["p_what"]
    except:
        print(f"No Pressure Selected...", file=sys.stderr)
        sys.exit(1)
    
    try:
        i = int(p_what.replace("P", ""))-1
        pressure = op_json["response"]["P2"][i]
        return pressure
    except:
        common_functions.patch_req("Report", report_id, body={"loading": "Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like P4", "is_loading_error": "no"}, dev=dev)
        print(f"Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like: P4", file=sys.stderr)
        sys.exit(1)

def get_acfm_entered(op_json, ac_id, dev):
    dataset_7_2_ids = op_json["response"]["dataset_7_2"]

    for dataset_7_2_id in dataset_7_2_ids:
        dataset_7_2_json = common_functions.get_req("dataset_7_2", dataset_7_2_id, dev)
        row_ac_id = dataset_7_2_json["response"]["air_compressor"]

        if row_ac_id == ac_id:
            acfm = dataset_7_2_json["response"]["acfm"]
            return acfm

def get_op_report_ac_kw(report_id, op_name, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    op_ids = report_json["response"]["operation_period"]

    kw = []
    for op_id in op_ids:
        op_json = common_functions.get_req("operation_period", op_id, dev)

        if op_json["response"]["Name"] == op_name:
            kw = op_json["response"]["kW"]
            return kw

def start():
    dev, report_id, scenario_id = get_payload()
    
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_baseline_id = scenario_json["response"]["scenario_baseline"]
    scenario_baseline_json = common_functions.get_req("scenario_baseline", scenario_baseline_id, dev)

    ac_ids = scenario_baseline_json["response"]["air_compressor"]
    operating_period_ids = scenario_baseline_json["response"]["operation_period"]


    for operating_period_id in operating_period_ids:
        avg_kws = []
        
        op_json = common_functions.get_req("operation_period", operating_period_id, dev)

        pressure = get_pressure_index(report_id, op_json, dev)

        for ac in ac_ids:

            acfm = get_acfm_entered(op_json, ac, dev)

            avg_kw = common_functions.calculate_kw_from_flow(ac, report_id, pressure, acfm, dev)
            avg_kws.append(avg_kw)
        
        op_avg_kw = sum(avg_kws)

        op_name = op_json["response"]["Name"]

        report_op_kw = get_op_report_ac_kw(report_id, op_name, dev)

        total_kw_change = op_avg_kw - report_op_kw

        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        try:
            scenario_differences = operating_period_json["response"]["scenario_differences"]
        except:
            scenario_differences = create_new_scenario_difference(operating_period_id, dev)

        common_functions.patch_req("scenario_differences", scenario_differences, body={"compressor_kw_change": total_kw_change}, dev=dev)

        baseline_global.update_op_stats(operating_period_id, report_id, dev)


start()
