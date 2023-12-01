import sys
import json
import common_functions
from datetime import datetime, timedelta

def get_num_leaks(report_json, dev):
    leak_id = report_json["response"]["leak"]
    leak_json = common_functions.get_req("leak", leak_id, dev)
    leak_entry_ids = leak_json["response"]["leak_entry"]
    num_leaks = len(leak_entry_ids)
    cfms = []
    for id in leak_entry_ids:
        leak_entry_json = common_functions.get_req("leak_entry", id, dev)
        cfms.append(leak_entry_json["response"]["cfm"])

    total_cfm = sum(cfms)
    return num_leaks, total_cfm

def get_section_8_1_inputs(eco_table_8_1_id, dev):
    eco_table_8_1_json = common_functions.get_req("eco_table_8_1", eco_table_8_1_id, dev)
    cost_per_leak_repair = eco_table_8_1_json["response"]["cost_per_leak_repair"]
    multiply_factor = eco_table_8_1_json["response"]["multiply_factor"]
    additional_value = eco_table_8_1_json["response"]["additional_value"]
    leak_incentive_value = eco_table_8_1_json["response"]["leak_incentive_value"]
    percent_or_o_and_m_symbol = eco_table_8_1_json["response"]["percent_or_o_and_m_symbol"]
    per_leak_or_kwh = eco_table_8_1_json["response"]["per_leak_or_kwh"]

    return cost_per_leak_repair, multiply_factor, additional_value, leak_incentive_value, percent_or_o_and_m_symbol, per_leak_or_kwh

def get_total_annual_operating_hours(report_json, dev):
    if report_json["response"]["operating_period_type"] != "Experimental":
        op_ids = report_json["response"]["operation_period"]
        hrs_yr = []
        for id in op_ids:
            op_json = common_functions.get_req("operation_period", id, dev)
            hrs = op_json["response"]["Hours/yr"]
            hrs_yr.append(hrs)
        
        total_hrs = sum(hrs_yr)

        return total_hrs
    else:
        op_ids = report_json["response"]["operation_period"]
        base_weekly_schedule = [False] * 10080
        for id in op_ids:
            _, weekly_schedule = common_functions.minutes_between_experimental(id, dev)
            for i in range(10080):
                if base_weekly_schedule[i] == False:   
                    base_weekly_schedule[i] = weekly_schedule[i]
        
        total_hrs = sum(base_weekly_schedule) / 60
        return total_hrs


def calculate_dollars_per_year(report_json, kw_demand_15min, kwh_annual, dev):
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

def conditional_value(per_leak_or_kwh, kwh_per_year, num_leaks):
    if per_leak_or_kwh == "kWh":
        return kwh_per_year
    else:
        return num_leaks

def conditional_value_2(per_leak_or_kwh, dollars_per_year, installed):
    if per_leak_or_kwh == "kWh":
        return dollars_per_year
    else:
        return installed

def calculate_incentive_estimate(leak_incentive_value, percent_or_o_and_m_symbol, per_leak_or_kwh, kwh_per_year, num_leaks, dollars_per_year, installed):
    #=IF(F13="$",F12*IF(F14="kWh",N11,B5),F12*IF(F14="kWh",N17,N5))

    if percent_or_o_and_m_symbol == "$":
        result = leak_incentive_value * conditional_value(per_leak_or_kwh, kwh_per_year, num_leaks)
    elif percent_or_o_and_m_symbol == "%":
        result = leak_incentive_value * conditional_value_2(per_leak_or_kwh, dollars_per_year, installed)
    
    return result

def get_baseline_kwh_per_year(report_json, dev):
    baseline_operation_7_1_id = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = common_functions.get_req("baseline_operation_7_1", baseline_operation_7_1_id, dev)
    baseline_row_ids = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    kwh_list = []
    for id in baseline_row_ids:
        baseline_row_json = common_functions.get_req("baseline_operation_7_1_row", id, dev)

        kwh_list.append(baseline_row_json["response"]["kwh_annual"])

    baseline_kwh_per_year = sum(kwh_list)
    return baseline_kwh_per_year

def get_dependencies(report_json, dev):
    num_leaks, total_cfm = get_num_leaks(report_json, dev)
    peak_acfm_15min = report_json["response"]["15 Min Peak Flow"]
    kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]
    total_op_hours = get_total_annual_operating_hours(report_json, dev)
    baseline_kwh_per_year = get_baseline_kwh_per_year(report_json, dev)

    return num_leaks, total_cfm,  peak_acfm_15min, kw_max_avg_15, total_op_hours, baseline_kwh_per_year

def get_body(installed, kw_demand, kwh_per_year, dollars_per_year, incentive_estimate, percent_or_o_and_m, payback_years):
    body = {
        "installed": installed,
        "incremental": installed,
        "kw_demand": kw_demand,
        "kw_max": kw_demand,
        "kwh_per_year": kwh_per_year,
        "dollars_per_year": dollars_per_year,
        "incentive_estimate": incentive_estimate,
        "percent_or_o_and_m": percent_or_o_and_m,
        "payback_years": payback_years
    }

    return body

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    # local_data = '{"report-id": "1696875806393x222632359563624450", "dev": "yes"}'

    # data = json.loads(data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    
    # Get the standard data
    report_id = data.get('report_id') # For report_json
    report_json = common_functions.get_req("report", report_id, dev) # For retrieving dependencies
    eco_table_8_1_id = data.get('eco_table_8_1_id') # For retreiving input values and sending back to the right spot

    # Gets all the dependencies
    num_leaks, total_cfm, peak_acfm_15min, kw_max_avg_15, total_op_hours, baseline_kwh_per_year = get_dependencies(report_json, dev)

    # Get's user inputs for this row in table 8.1
    cost_per_leak_repair, multiply_factor, additional_value, leak_incentive_value, percent_or_o_and_m_symbol, per_leak_or_kwh = get_section_8_1_inputs(eco_table_8_1_id, dev)

    # Calculates Installed and Incremental Value
    installed = (cost_per_leak_repair * num_leaks + additional_value) * multiply_factor

    # Calculates kW Demand and kW Max
    kw_demand = kw_max_avg_15 / peak_acfm_15min * total_cfm

    # Calculates total kWhs per year
    kwh_per_year = kw_demand * total_op_hours

    # Calculates the amount spent per year on electricity lost through leaks
    dollars_per_year = calculate_dollars_per_year(report_json, kw_max_avg_15, kwh_per_year, dev)

    # Calculates the Insentive estimate
    incentive_estimate = calculate_incentive_estimate(leak_incentive_value, percent_or_o_and_m_symbol, per_leak_or_kwh, kwh_per_year, num_leaks, dollars_per_year, installed)

    # Calculates the percentage of kWh per year you are using on leaks (Leaks are always % not $ values)
    percent_or_o_and_m = kwh_per_year / baseline_kwh_per_year

    payback_years = ((installed - incentive_estimate) / dollars_per_year) + (percent_or_o_and_m if percent_or_o_and_m_symbol == "$" else 0)

    # Assembles the body json to be sent back to Bubble.io
    body = get_body(installed, kw_demand, kwh_per_year, dollars_per_year, incentive_estimate, percent_or_o_and_m, payback_years)

    # Sending the final calculations back to Bubble.io
    common_functions.patch_req("eco_table_8_1", eco_table_8_1_id, body, dev)


start()