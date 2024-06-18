import os
import sys
import json
from eco_calculation import proposed_global

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

def get_flow_reduction(avg_pressure, percent_leaks, percent_poorly_regulated, avg_cfm, target_pressure):
    psi_reduction = target_pressure - avg_pressure
    print(f"psi_reduction: {psi_reduction}")

    new_leak_acfm = ((percent_leaks * avg_cfm) + (percent_leaks * avg_cfm) * psi_reduction / 100)
    poorly_regulated_acfm = ((percent_poorly_regulated * avg_cfm) + (percent_poorly_regulated * avg_cfm) * psi_reduction / 100)
    properly_regulated_acfm = (1 - (percent_poorly_regulated + percent_leaks)) * avg_cfm
    print(f"new_leak_acfm: {new_leak_acfm}, poorly_regulated_acfm: {poorly_regulated_acfm}, properly_regulated_acfm: {properly_regulated_acfm}")

    return (new_leak_acfm + poorly_regulated_acfm + properly_regulated_acfm) - avg_cfm


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

def get_peak_acfm(op_json, dev):
    dataset_7_2_ids = op_json["response"]["dataset_7_2"]

    peak_acfms = []
    for dataset_7_2_id in dataset_7_2_ids:
        dataset_7_2_json = common_functions.get_req("dataset_7_2", dataset_7_2_id, dev)
        
        peak_acfm = dataset_7_2_json["response"]["peak-15-acfm"]
        peak_acfms.append(peak_acfm)
    
    return sum(peak_acfms)

def get_low_pressure(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    pressure_sensor_ids = report_json["response"]["pressure_sensor"]

    for pressure_sensor_id in pressure_sensor_ids:
        pressure_json = common_functions.get_req("pressure_sensor", pressure_sensor_id, dev)
        header = pressure_json["response"]["header"]
        if header == True:
            return pressure_json["response"]["15-min-low"]


def start():
    dev, report_id, scenario_id = get_payload()

    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    op_ids = scenario_proposed_json["response"]["operation_period"]

    pressure_id = scenario_proposed_json["response"]["pressure"]
    pressure_json = common_functions.get_req("pressure", pressure_id, dev)
    target_pressure = pressure_json["response"]["target_pressure"]
    percent_leaks = pressure_json["response"]["percent_leaks"]
    print(f"percent_leaks: {percent_leaks}")
    percent_poorly_regulated = pressure_json["response"]["percent_poorly_regulated"]
    print(f"percent_poorly_regulated: {percent_poorly_regulated}")

    for op_id in op_ids:
        op_json = common_functions.get_req("operation_period", op_id, dev)
        op_name = op_json["response"]["Name"]
        print("")
        print(f"Schedule: {op_name}")

        # Get's the average header pressure in report. Will be something like "107.422313453"
        avg_pressure = get_pressure_index(report_id, op_json, dev)
        avg_cfm = op_json["response"]["ACFM Made"]
        # avg_cfm = 32.5
        print("")
        print(f"AVERAGE:")
        print(f"avg_cfm: {avg_cfm}")
        print(f"avg_pressure: {avg_pressure}")
        avg_acfm_change = get_flow_reduction(avg_pressure, percent_leaks, percent_poorly_regulated, avg_cfm, target_pressure)
        print(f"avg_acfm_change: {avg_acfm_change}")
        
        peak_cfm = get_peak_acfm(op_json, dev)
        # peak_cfm = 244.5
        low_pressure = get_low_pressure(report_id, dev) # Currently get's the global 15 min low because I'm lazy
        print("")
        print(f"PEAK:")
        print(f"peak_cfm: {peak_cfm}")
        print(f"low_pressure: {low_pressure}")
        peak_acfm_change = get_flow_reduction(low_pressure, percent_leaks, percent_poorly_regulated, peak_cfm, target_pressure)
        print(f"peak_acfm_change: {peak_acfm_change}")
        print("")



if __name__ == "__main__":
    start()