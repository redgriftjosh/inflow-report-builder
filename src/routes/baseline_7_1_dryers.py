import sys
import json
import common_functions
from datetime import datetime, timedelta

# print("All Good")
# sys.exit()

# Get's the operating period ID so you can pull data you need from it.
def get_dryers(report_id, dev):
    report_json = common_functions.get_req("Report", report_id, dev)

    if "dryer" in report_json["response"] and report_json["response"]["dryer"] != []:
        dryer_ids = report_json["response"]["dryer"]

        adjusted_kws = []
        
        for dryer_id in dryer_ids:
            dryer_json = common_functions.get_req("dryer", dryer_id, dev)
            try:
                full_load_kw = dryer_json["response"]["full_load_kw"]
            except:
                print(f"Having a hard time getting Full Load kW from some of your dryers. Do you have some empty values over there?", file=sys.stderr)
                sys.exit(1)

            try:
                pf = dryer_json["response"]["pf"]
            except:
                pf = 1
            
            adjusted_kw = full_load_kw * pf
            adjusted_kws.append(adjusted_kw)

        return sum(adjusted_kws)

    else:
        print(f"Error: No Dryers Found! You need at least one Dryer.", file=sys.stderr)
        sys.exit(1)

def calculate_cost_to_operate(report_json, kw_demand_15min, kwh_annual, dev):
    elec_provider_id = report_json["response"]["electrical_provider"]
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

    blended_on_peak = sum(kwh_on_peak_list) / len(kwh_on_peak_list)
    blended_off_peak = sum(kwh_off_peak_list) / len(kwh_off_peak_list)

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

    cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))

    return cost_to_operate

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

    baseline_operation_7_1_row_id = data.get('baseline_operation_7_1_row_id')

    common_functions.patch_req("Report", report_id, body={"loading": f"Getting Data From your dryers...", "is_loading_error": "no"}, dev=dev)
    kw_demand_15min = get_dryers(report_id, dev)

    kwh_annual = kw_demand_15min * 8760 # Change to total operational hours

    average_kw_demand = kwh_annual / 8760 # Change to total operational hours

    cost_to_operate = calculate_cost_to_operate(report_json, kw_demand_15min, kwh_annual, dev)

    body = {
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "label": "Dryers"
    }

    common_functions.patch_req("baseline_operation_7_1_row", baseline_operation_7_1_row_id, body, dev)
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

start()
