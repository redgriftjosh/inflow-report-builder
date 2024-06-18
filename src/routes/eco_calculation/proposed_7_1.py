import sys, os
from datetime import datetime, timedelta
print("Hello from proposed_7_1.py2")
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../')))
from utilities import baseline_proposed_7_1_util
print("Hello from proposed_7_1.py3")
current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions


def get_baseline_operation_7_1_id(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    baseline_operation_7_1_id = scenario_proposed_json["response"]["baseline_operation_7_1"]

    return baseline_operation_7_1_id

def get_report_baseline_operation_7_1(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]

    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)

    return baseline_operation_7_1_json

def get_scenario_demand_schedule_id(report_id, scenario_id, dev):
    report_baseline_operation_7_1_json = get_report_baseline_operation_7_1(report_id, dev)
    report_demand_schedule_id = report_baseline_operation_7_1_json["response"]["demand_schedule_id"]

    report_demand_schedule_json = common_functions.get_req("operation_period", report_demand_schedule_id, dev)

    op_name = report_demand_schedule_json["response"]["Name"]

    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    op_ids = scenario_proposed_json["response"]["operation_period"]

    for op_id in op_ids:
        op_json = common_functions.get_req("operation_period", op_id, dev)

        if op_json["response"]["Name"] == op_name:
            demand_schedule_id = op_json["response"]["_id"]
            return demand_schedule_id

def check_dependencies(report_id, scenario_id, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Checking Dependencies...", "is_loading_error": "no"}, dev=dev)
    report_json = common_functions.get_req("report", report_id, dev)
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]
    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    # Checking if we have at least one operation period
    try:
        operation_period_ids = scenario_proposed_json["response"]["operation_period"] 
    except:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)

    baseline_operation_7_1 = get_baseline_operation_7_1_id(scenario_id, dev)

    demand_schedule_id = get_scenario_demand_schedule_id(report_id, scenario_id, dev)
    
    return operation_period_ids, report_json, baseline_operation_7_1, demand_schedule_id

def reset_rows(baseline_operation_7_1, report_id, report_json, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Resetting Any Existing Data...", "is_loading_error": "no"}, dev=dev)

    # baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    # try:

    # except:
    #     baseline_operation_7_1 = create_first_baseline_operation_7_1(report_id, dev)
    
    # Deleting any rows if they exist
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)
    try:
        baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

        for row in baseline_operation_7_1_rows:
            common_functions.del_req("baseline_operation_7_1_row", row, dev)
    except:
        print(f"No Rows Found, I guess")

    common_functions.patch_req("Report", report_id, body={"loading": f"Getting started on the Calculations...", "is_loading_error": "no"}, dev=dev)

    return baseline_operation_7_1

def start(dev, report_id, scenario_id, scope):
    print("Hello from proposed_7_1.py")

    operation_period_ids, report_json, baseline_operation_7_1, demand_schedule_id = check_dependencies(report_id, scenario_id, dev)

    baseline_operation_7_1 = reset_rows(baseline_operation_7_1, report_id, report_json, dev)
    # start_calculations(operation_period_ids, report_json, baseline_operation_7_1, scenario_id, demand_schedule_id, dev)
    baseline_proposed_7_1_util.start_calculations(operation_period_ids, demand_schedule_id, report_json, baseline_operation_7_1, dev, scope)

if __name__ == "__main__":
    start()