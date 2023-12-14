import sys
import json
import common_functions
from datetime import datetime, timedelta

# Make sure we have everything we need before running
def check_dependencies(report_id, report_json, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Checking Dependencies...", "is_loading_error": "no"}, dev=dev)

    # Checking if we have at least one operation period
    try:
        operation_period_ids = report_json["response"]["operation_period"]
    except:
        print(f"No Operating Periods found! You need at least on operation period...", file=sys.stderr)
        sys.exit(1)

    # Checking if we have the necessary data from section 3.2
    try:
        peak_acfm_15 = report_json["response"]["15 Min Peak Flow"]
        kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]
    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    # Checking if we have electrical utility providers entered
    try:
        electrical_provider = report_json["response"]["electrical_provider"]

        electrical_provider_json = common_functions.get_req("electrical_provider", electrical_provider, dev)
        on_peak_start = electrical_provider_json["response"]["on_peak_start"]
        off_peak_start = electrical_provider_json["response"]["off_peak_start"]

        electrical_provider_entrys = electrical_provider_json["response"]["electrical_provider_entry"]

    except:
        print(f"You'll need to run Section 3.2 before you run this one...", file=sys.stderr)
        sys.exit(1)
    
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    demand_schedule_id = baseline_operation_7_1_json["response"]["demand_schedule_id"]
    # try:
    # except Exception as e:
    #     print(f"Please Select an Operation Period to define the Demand calculations...{e}", file=sys.stderr)
    #     sys.exit(1)

    
    return on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id, kw_max_avg_15
    

def create_first_baseline_operation_7_1(report_id, dev):
    response = common_functions.post_req("baseline_operation_7_1", body={"report": report_id}, dev=dev)
    baseline_operation_7_1 = response["id"]

    common_functions.patch_req("report", report_id, body={"baseline_operation_7_1": baseline_operation_7_1}, dev=dev)
    
    return baseline_operation_7_1

def reset_rows(report_id, report_json, dev):
    common_functions.patch_req("Report", report_id, body={"loading": f"Resetting Any Existing Data...", "is_loading_error": "no"}, dev=dev)

    try:
        baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]

    except:
        baseline_operation_7_1 = create_first_baseline_operation_7_1(report_id, dev)
    
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

    if op_id == demand_schedule_id:
        cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    else:
        cost_to_operate = (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))

    return cost_to_operate

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
    
def calculate_row(report_json, kw_demand_15min, demand_schedule_id, op_id, op_json, baseline_operation_7_1, dev):
    
    print(f"REPORT JSON: {report_json}")
    report_id = report_json["response"]["_id"]

    try:
        average_acfm = op_json["response"]["ACFM Made"]
        peak_15min_acfm = op_json["response"]["peak_15min_acfm"]
        average_kw_demand = op_json["response"]["kW"]
        hours_annual = op_json["response"]["Hours/yr"]
        kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    except:
        print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
        sys.exit(1)


    pressure = get_pressure_index(report_id, op_json, dev)

    kwh_annual = average_kw_demand * hours_annual

    cost_to_operate = get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev)

    label = op_json["response"]["Name"]

    body = {
        "peak_15min_acfm": peak_15min_acfm,
        "average_acfm": average_acfm,
        "pressure": pressure,
        "hours_annual": hours_annual,
        "average_kw_demand": average_kw_demand,
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




def start_calculations(operation_period_ids, demand_schedule_id, report_json, kw_demand_15min, baseline_operation_7_1, dev):

    row_ids = []

    for operation_period_id in operation_period_ids:
        op_json = common_functions.get_req("operation_period", operation_period_id, dev)
        
        row_id = calculate_row(report_json, kw_demand_15min, demand_schedule_id, operation_period_id, op_json, baseline_operation_7_1, dev)
        row_ids.append(row_id)


    patch_response = common_functions.patch_req("baseline_operation_7_1", baseline_operation_7_1, body={"baseline_operation_7_1_row": row_ids}, dev=dev)
    print(f"PATCH REQ RESPONSE: {patch_response}")

    



def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    # local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    report_json = common_functions.get_req("Report", report_id, dev)

    # Make sure we have everything we need before running
    on_peak_start, off_peak_start, operation_period_ids, demand_schedule_id, kw_demand_15min = check_dependencies(report_id, report_json, dev)

    # Delete any existing rows
    baseline_operation_7_1 = reset_rows(report_id, report_json, dev)

    # Run Calculations for each Operation Period
    start_calculations(operation_period_ids, demand_schedule_id, report_json, kw_demand_15min, baseline_operation_7_1, dev)



start()


