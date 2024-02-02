import sys
import os

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions

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

def dataset_7_2_calculations(report_id, operating_period_id, ac, acfm, pressure, dev):
    
    avg_kw = common_functions.calculate_kw_from_flow(ac, report_id, pressure, acfm, dev)

    max_cfm = common_functions.get_max_cfm(ac, dev)

    flow_percent = (acfm/max_cfm) * 100

    # ready for webhook
    body = {
        "kw": avg_kw,
        "acfm": acfm,
        "flow-percent": flow_percent,
        }
    
    print(f"body: {body}")
    # Send the patch to the dataset linked to the right air compressor 
    operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
    dataset_ids = operating_period_json["response"]["dataset_7_2"]
    for dataset_id in dataset_ids:
        dataset_json = common_functions.get_req("dataset_7_2", dataset_id, dev)
        if dataset_json["response"]["air_compressor"] == ac:
            common_functions.patch_req("dataset_7_2", dataset_id, body, dev)

def start(dev, report_id, scenario_id):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    ac_ids = scenario_proposed_json["response"]["air_compressor"]
    operating_period_ids = scenario_proposed_json["response"]["operation_period"]

    for ac in ac_ids:

        for operating_period_id in operating_period_ids:

            op_json = common_functions.get_req("operation_period", operating_period_id, dev)

            pressure = get_pressure_index(report_id, op_json, dev)
            acfm = get_acfm_entered(op_json, ac, dev)
            
            dataset_7_2_calculations(report_id, operating_period_id, ac, acfm, pressure, dev)

    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)