import sys
from datetime import datetime, timedelta
import os

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



def get_avg_kw(scenario_id, report_id, pressure, acfm, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    print(f"scenario_json: {scenario_json}")
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)

    ac_ids = scenario_proposed_json["response"]["air_compressor"]

    for ac_id in ac_ids:
        print(f"ac_id: {ac_id}")
        avg_kw = common_functions.calculate_kw_from_flow(ac_id, report_id, pressure, acfm, dev)

    return avg_kw

def get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev):
    try:
        elec_provider_id = report_json["response"]["electrical_provider"]
    except:
        print(f"Can't find any Electrical Utility info!", file=sys.stderr)
        sys.exit(1)
    elec_provider_json = common_functions.get_req("electrical_provider", elec_provider_id, dev)
    elec_entry_ids = elec_provider_json["response"]["electrical_provider_entry"]

    on_peak_list = []

    kwh_on_peak_list = []
    kwh_off_peak_list = []

    for elec_entry_id in elec_entry_ids:
        elec_entry_json = common_functions.get_req("electrical_provider_entry", elec_entry_id, dev)
        month_start = datetime.strptime(elec_entry_json["response"]["month_start"], "%B").month
        month_end = datetime.strptime(elec_entry_json["response"]["month_end"], "%B").month
        kw_on_peak = elec_entry_json["response"]["kw_on_peak"]

        if month_start <= month_end:
            num_months = month_end - month_start + 1
        else:
            # If the start month is after the end month, it implies the end month is in the next year
            num_months = (12 - month_start) + month_end + 1
        
        on_peak = kw_demand_15min * kw_on_peak * num_months
            
        on_peak_list.append(on_peak)

        kwh_on_peak = elec_entry_json["response"]["kwh_on_peak"] * (num_months / 12)
        kwh_on_peak_list.append(kwh_on_peak)

        kwh_off_peak = elec_entry_json["response"]["kwh_off_peak"] * (num_months / 12)
        kwh_off_peak_list.append(kwh_off_peak)

    blended_on_peak = sum(kwh_on_peak_list)
    blended_off_peak = sum(kwh_off_peak_list)

    on_peak_start = datetime.strptime(elec_provider_json["response"]["on_peak_start"], '%I:%M %p').time()
    off_peak_start = datetime.strptime(elec_provider_json["response"]["off_peak_start"], '%I:%M %p').time()

    # Create datetime objects by combining the time with today's date
    today = datetime.today().date()
    on_peak_start_dt = datetime.combine(today, on_peak_start)
    off_peak_start_dt = datetime.combine(today, off_peak_start)

    # If off_peak_start is the next day
    if off_peak_start < on_peak_start:
        off_peak_start_dt += timedelta(days=1)

    # Calculate the difference between the two datetime objects
    on_peak_seconds = (off_peak_start_dt - on_peak_start_dt).total_seconds()

    on_peak_days = on_peak_seconds / (24 * 60 * 60)

    if op_id == demand_schedule_id or demand_schedule_id == "Dryers":
        cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    else:
        cost_to_operate = (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    # if op_id == demand_schedule_id:
    #     cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    # else:

    return cost_to_operate

def get_peak_15_acfm(op_json, dev):
    peak_15min_acfm = op_json["response"]["peak_15min_acfm"]

    scenario_differences_id = op_json["response"]["scenario_differences"]
    scenario_differences_json = common_functions.get_req("scenario_differences", scenario_differences_id, dev)
    
    # drain_cfm_change = scenario_differences_json["response"]["drain_cfm_change"]
    # dryer_cfm_change = scenario_differences_json["response"]["dryer_cfm_change"]
    try:
        leak_cfm_change = scenario_differences_json["response"]["dryer_cfm_change"]
    except:
        leak_cfm_change = 0
        print("no pleak_cfm_change")
    
    try:
        drain_cfm_change = scenario_differences_json["response"]["drain_cfm_change"]
    except:
        drain_cfm_change = 0
        print("no pleak_cfm_change")
    
    try:
        dryer_cfm_change = scenario_differences_json["response"]["dryer_cfm_change"]
    except:
        dryer_cfm_change = 0
        print("no pleak_cfm_change")

    cfm_change = drain_cfm_change + dryer_cfm_change + leak_cfm_change

    new_15_acfm = peak_15min_acfm + cfm_change

    return new_15_acfm

def get_kw_demand_15min(report_json, op_json, dev):
    kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    scenario_differences_id = op_json["response"]["scenario_differences"]
    scenario_differences_json = common_functions.get_req("scenario_differences", scenario_differences_id, dev)
    
    compressor_kw_change = scenario_differences_json["response"]["drain_cfm_change"]
    dryer_kw_change = scenario_differences_json["response"]["dryer_cfm_change"]

    kw_change = compressor_kw_change + dryer_kw_change

    new_15_kw = kw_demand_15min + kw_change

    return new_15_kw

def calculate_row(report_json, op_id, op_json, baseline_operation_7_1, scenario_id, demand_schedule_id, dev):
    
    print(f"REPORT JSON: {report_json}")
    report_id = report_json["response"]["_id"]

    if op_id == demand_schedule_id:
        kw_demand_15min = get_kw_demand_15min(report_json, op_json, dev)
    else:
        kw_demand_15min = report_json["response"]["kw_max_avg_15"]
    
    peak_15min_acfm = get_peak_15_acfm(op_json, dev)


    try:
        average_acfm = op_json["response"]["ACFM Made"]
        hours_annual = op_json["response"]["Hours/yr"]
        avg_kw = op_json["response"]["kW"]

    except:
        print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
        sys.exit(1)


    pressure = get_pressure_index(report_id, op_json, dev) # Average Header PSIG For this Operation period

    kwh_annual = avg_kw * hours_annual

    cost_to_operate = get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev)

    label = op_json["response"]["Name"]

    body = {
        "peak_15min_acfm": peak_15min_acfm,
        "average_acfm": average_acfm,
        "pressure": pressure,
        "hours_annual": hours_annual,
        "average_kw_demand": avg_kw,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    if demand_schedule_id == op_id:
        body["kw_demand_15min"] = kw_demand_15min


    response = common_functions.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def get_report_dryer_kw(report_json, dev):
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    for row in baseline_operation_7_1_rows:
        row_json = common_functions.get_req("baseline_operation_7_1_row", row, dev)
        label = row_json["response"]["label"]

        if label == "Dryers":
            average_kw_demand = row_json["response"]["average_kw_demand"]
            return average_kw_demand

def calculate_dryer_row(report_json, baseline_operation_7_1, kw, dev):
    
    kw_demand_15min = kw
    average_kw_demand = kw

    total_hours = report_json["response"]["total_hours"]

    kwh_annual = average_kw_demand * total_hours

    cost_to_operate = get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id="Dryers", op_id=None, dev=dev)

    label = "Dryers"

    body = {
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    response = common_functions.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def calculate_dryer(report_json, scenario_id, operation_period_ids, baseline_operation_7_1, dev):
    kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    dryer_kw_changes = []
    for operation_period_id in operation_period_ids:
        op_json = common_functions.get_req("operation_period", operation_period_id, dev)

        scenario_differences_id = op_json["response"]["scenario_differences"]
        scenario_differences_json = common_functions.get_req("scenario_differences", scenario_differences_id, dev)

        try:
            dryer_kw_change = scenario_differences_json["response"]["dryer_kw_change"]
            dryer_kw_changes.append(dryer_kw_change)
        except:
            print("no dryer_kw_change")
    
    avg_dryer_kw_change = sum(dryer_kw_changes)/len(dryer_kw_changes)

    report_dryer_kw = get_report_dryer_kw(report_json, dev)

    new_dryer_kw = report_dryer_kw + avg_dryer_kw_change

    row_id = calculate_dryer_row(report_json, baseline_operation_7_1, new_dryer_kw, dev)

    return row_id

def start_calculations(operation_period_ids, report_json, baseline_operation_7_1, scenario_id, demand_schedule_id, dev):

    row_ids = []

    for operation_period_id in operation_period_ids:
        op_json = common_functions.get_req("operation_period", operation_period_id, dev)
        
        row_id = calculate_row(report_json, operation_period_id, op_json, baseline_operation_7_1, scenario_id, demand_schedule_id, dev)
        row_ids.append(row_id)
    
    row_id = calculate_dryer(report_json, scenario_id, operation_period_ids, baseline_operation_7_1, dev)
    row_ids.append(row_id)

    # row_id = calculate_dryers()
    patch_response = common_functions.patch_req("baseline_operation_7_1", baseline_operation_7_1, body={"baseline_operation_7_1_row": row_ids}, dev=dev)
    print(f"PATCH REQ RESPONSE: {patch_response}")

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

def start(dev, report_id, scenario_id):

    operation_period_ids, report_json, baseline_operation_7_1, demand_schedule_id = check_dependencies(report_id, scenario_id, dev)

    baseline_operation_7_1 = reset_rows(baseline_operation_7_1, report_id, report_json, dev)

    start_calculations(operation_period_ids, report_json, baseline_operation_7_1, scenario_id, demand_schedule_id, dev)