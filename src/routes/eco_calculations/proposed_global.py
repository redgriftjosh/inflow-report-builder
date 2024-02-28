import os
import sys

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions

def get_report_pressure(report_id, op_name, dev):
    report_json = common_functions.get_req("Report", report_id, dev)
    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)

    operation_period_ids = report_json["response"]["operation_period"]

    try:
        p_what = baseline_operation_7_1_json["response"]["p_what"]
    except:
        print(f"No Pressure Selected...", file=sys.stderr)
        sys.exit(1)
    
    for operating_period_id in operation_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        if operating_period_json["response"]["Name"] == op_name:
            i = int(p_what.replace("P", ""))-1
            pressure = operating_period_json["response"]["P2"][i]
            pressure_list = operating_period_json["response"]["P2"]
            return pressure, i, pressure_list
            
def get_real_op_avg_acfm(report_id, op_name, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    # avg_acfm = report_json["response"]["avg_acfm"]

    operation_period_ids = report_json["response"]["operation_period"]

    for operating_period_id in operation_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        if operating_period_json["response"]["Name"] == op_name:
            acfm = operating_period_json["response"]["ACFM Made"]
            return acfm

def get_real_op_peak_acfm(report_id, op_name, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    # avg_acfm = report_json["response"]["avg_acfm"]

    operation_period_ids = report_json["response"]["operation_period"]

    for operating_period_id in operation_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        if operating_period_json["response"]["Name"] == op_name:
            acfm = operating_period_json["response"]["peak_15min_acfm"]
            return acfm

def get_real_op_avg_kw(report_id, op_name, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    # avg_acfm = report_json["response"]["avg_acfm"]

    operation_period_ids = report_json["response"]["operation_period"]

    for operating_period_id in operation_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        if operating_period_json["response"]["Name"] == op_name:
            kw = operating_period_json["response"]["kW"]
            return kw



def update_op_stats(op_id, report_id, dev):
    op_json = common_functions.get_req("operation_period", op_id, dev)
    scenario_differences = op_json["response"]["scenario_differences"]

    scenario_differences_json = common_functions.get_req("scenario_differences", scenario_differences, dev)

    cfm_changes = []

    try:
        leak_cfm_change = scenario_differences_json["response"]["leak_cfm_change"]
        cfm_changes.append(leak_cfm_change)
    except:
        print(f"No leak_cfm_change")

    try:
        drain_cfm_change = scenario_differences_json["response"]["drain_cfm_change"]
        cfm_changes.append(drain_cfm_change)
    except:
        print(f"No drain_cfm_change")

    try:
        dryer_cfm_change = scenario_differences_json["response"]["dryer_cfm_change"]
        cfm_changes.append(dryer_cfm_change)
    except:
        print(f"No dryer_cfm_change")

    total_cfm_changes = sum(cfm_changes)

    op_name = op_json["response"]["Name"]

    orig_acfm = get_real_op_avg_acfm(report_id, op_name, dev)

    orig_peak_acfm = get_real_op_peak_acfm(report_id, op_name, dev)

    new_acfm = orig_acfm + total_cfm_changes

    new_peak_acfm = orig_peak_acfm + total_cfm_changes

    print(f"orig_acfm: {orig_acfm}")
    print(f"orig_peak_acfm: {orig_peak_acfm}")
    print(f"new_acfm: {new_acfm}")
    print(f"new_peak_acfm: {new_peak_acfm}")


    kw_changes = []
    try:
        dryer_kw_change = scenario_differences_json["response"]["dryer_kw_change"]
        kw_changes.append(dryer_kw_change)
    except:
        print(f"No dryer_kw_change")
    
    try:
        compressor_kw_change = scenario_differences_json["response"]["compressor_kw_change"]
        kw_changes.append(compressor_kw_change)
    except:
        print(f"No compressor_kw_change")
    
    total_kw_changes = sum(kw_changes)

    orig_kw = get_real_op_avg_kw(report_id, op_name, dev)

    new_kw = orig_kw + total_kw_changes


    psi_changes = []
    try:
        filter_psi_change = scenario_differences_json["response"]["filter_psi_change"]
        psi_changes.append(filter_psi_change)
    except:
        print(f"No filter_psi_change")
    
    
    total_psi_changes = sum(psi_changes)

    orig_psi, i, pressure_list = get_report_pressure(report_id, op_name, dev)

    new_psi = orig_psi + total_psi_changes

    pressure_list[i] = new_psi

    common_functions.patch_req("operation_period", op_id, body={"P2": pressure_list, "kW": new_kw, "ACFM Made": new_acfm, "peak_15min_acfm": new_peak_acfm}, dev=dev)

    scenario_differences = op_json["response"]["scenario_differences"]

    common_functions.patch_req("scenario_differences", scenario_differences, body={"orig_psi": orig_psi, "orig_kw": orig_kw, "orig_acfm": orig_acfm}, dev=dev)

