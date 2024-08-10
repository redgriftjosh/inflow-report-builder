import common_functions
# import math
from datetime import datetime, timedelta
import sys
from utilities import requests_util

# dev = "/version-test"
# report_id = "1709055608768x171027315936985100"
# ac_id = "1709057325709x609322153994616800"
# ac_json = requests_util.get_req("air_compressor", ac_id, dev)
# cfm = 500.8
# volts = 480
# rated_psig = 115
# setpoint_psig = 107
# pf = 0.97
# pressure = 107
# acfm = 237


# a, b, c = common_functions.get_inverse_polynomial_vars(report_id, ac_json, cfm, volts, rated_psig, setpoint_psig, pf, pressure, dev)

# amps = (a * (acfm * acfm) + b * acfm + c)
# idle_kw = (amps * math.sqrt(3) * pf * volts) / 1000

# print(f"a: {a}")
# print(f"b: {b}")
# print(f"c: {c}")

# print(f"amps: {amps}")
# print(f"idle_kw: {idle_kw}")

dev = "/version-test"
report_id = "1706793868748x328693151843483650"
report_json = requests_util.get_req("report", report_id, dev)

kw_demand_15min = 63.6

kwh_annual = 43662



try:
    elec_provider_id = report_json["response"]["electrical_provider"]
except:
    print(f"Can't find any Electrical Utility info!", file=sys.stderr)
    sys.exit(1)
elec_provider_json = requests_util.get_req("electrical_provider", elec_provider_id, dev)
elec_entry_ids = elec_provider_json["response"]["electrical_provider_entry"]

on_peak_list = []

kwh_on_peak_list = []
kwh_off_peak_list = []

for elec_entry_id in elec_entry_ids:
    elec_entry_json = requests_util.get_req("electrical_provider_entry", elec_entry_id, dev)
    month_start = datetime.strptime(elec_entry_json["response"]["month_start"], "%B").month
    month_end = datetime.strptime(elec_entry_json["response"]["month_end"], "%B").month
    kw_on_peak = elec_entry_json["response"]["kw_on_peak"]

    if month_start <= month_end:
        num_months = month_end - month_start + 1
    else:
        # If the start month is after the end month, it implies the end month is in the next year
        num_months = (12 - month_start) + month_end + 1
    
    print(f"num_months: {num_months}")
    print(f"kw_on_peak: {kw_on_peak}")
    on_peak = kw_demand_15min * kw_on_peak * num_months
        
    on_peak_list.append(on_peak)
    print(f"on_peak: {on_peak}")

    kwh_on_peak = elec_entry_json["response"]["kwh_on_peak"] * (num_months / 12)
    kwh_on_peak_list.append(kwh_on_peak)
    print(f"kwh_on_peak: {kwh_on_peak}")

    kwh_off_peak = elec_entry_json["response"]["kwh_off_peak"] * (num_months / 12)
    kwh_off_peak_list.append(kwh_off_peak)
    print(f"kwh_off_peak: {kwh_off_peak}")
    print("")
print("")

blended_on_peak = sum(kwh_on_peak_list)
blended_off_peak = sum(kwh_off_peak_list)
print(f"blended_on_peak: {blended_on_peak}")
print(f"blended_off_peak: {blended_off_peak}")

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
print(f"on_peak_days: {on_peak_days}")

# Demand Schedule
# cost_to_operate = sum(on_peak_list) + (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
cost_to_operate = (kwh_annual * blended_on_peak * on_peak_days) + (kwh_annual * blended_off_peak * (1 - on_peak_days))
print(cost_to_operate)

# if op_id == demand_schedule_id or demand_schedule_id == "Dryers":
# else:




