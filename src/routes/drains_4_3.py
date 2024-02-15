import json
import sys
import common_functions
from datetime import datetime, timedelta

def get_payload():
    data = json.loads(sys.argv[1])

    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data.get('report_id')
    return dev, report_id

def get_drains(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    
    try:
        return report_json["response"]["drain"]
    except:
        print(f"Can't find any drains...?", "is_loading_error", file=sys.stderr)
        sys.exit(1)

def get_kw_per_year(drain, peak_acfm_15_min, kw_max_avg_15, dev):
    drain_json = common_functions.get_req("drain", drain, dev)

    try:
        off_min = drain_json["response"]["baseline_off_min"]
        on_sec = drain_json["response"]["baseline_on_sec"]

        try:
            acfm_loss = drain_json["response"]["acfm_loss"]
        except:
            acfm_loss = 0
        
        cycles_per_hour = 0 if off_min < 0.1 else 60 / off_min

        cf_per_cycle = on_sec * (52 / 60) # Currently hard coding 52 CFM can get through the drain

        total_acfm_loss = acfm_loss + (cycles_per_hour * cf_per_cycle / 60)


        return total_acfm_loss + kw_max_avg_15 / peak_acfm_15_min
    except:
        return 0



def get_global_values(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    try:
        peak_acfm_15_min = report_json["response"]["15 Min Peak Flow"]
        kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]

    except:
        print(f"I need Peak 15 Minute kW and ACFM from table 3.2... Did you already run that?", file=sys.stderr)
        sys.exit(1)
    
    hours_annual = common_functions.get_total_annual_operating_hours(report_json, dev)

    return peak_acfm_15_min, kw_max_avg_15, hours_annual, report_json
    

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

    if op_id == demand_schedule_id or demand_schedule_id == "Drains":
        cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
    else:
        cost_to_operate = (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))

    return cost_to_operate

def start():
    # Grab the variabls from the json payload
    dev, report_id = get_payload()

    # We need 15 minute peak acfm and 15 minute peak kw
    peak_acfm_15_min, kw_max_avg_15, hours_annual, report_json = get_global_values(report_id, dev)
    print(f"hours_annual: {hours_annual}")
    print(f"peak_acfm_15_min: {peak_acfm_15_min}")
    print(f"kw_max_avg_15: {kw_max_avg_15}")

    # Get array of drain IDs
    drains = get_drains(report_id, dev)

    #loop through each drain to start calculations
    for drain in drains:
        kw_per_year = get_kw_per_year(drain, peak_acfm_15_min, kw_max_avg_15, dev)
        print(f"kw_per_year: {kw_per_year}")

        kwh_annual = kw_per_year * hours_annual
        print(f"kwh_annual: {kwh_annual}")

        if kwh_annual != 0:
            cost_to_operate = get_cost_to_operate(report_json, kw_max_avg_15, kwh_annual, demand_schedule_id="no demand schedules", op_id="no", dev=dev)
            print(f"cost_to_operate: {cost_to_operate}")
            common_functions.patch_req("drain", drain, body={"cost_per_yr": cost_to_operate, "kw_per_yr": kwh_annual}, dev=dev)
        else:
            cost_to_operate = 0
            print(f"cost_to_operate: {cost_to_operate}")
            common_functions.patch_req("drain", drain, body={"cost_per_yr": cost_to_operate, "kw_per_yr": kwh_annual}, dev=dev)

    

start()