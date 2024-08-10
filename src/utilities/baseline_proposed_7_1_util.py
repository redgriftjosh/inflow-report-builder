# This figure is called from the report, proposed scenarios, and baseline scenarios.

import sys
import json
from routes import common_functions
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from utilities import data_crunch_util, financial_util, dryers_util, requests_util, pressure_util


def get_kw_demand_15min(report_json, op_json, dev):
    kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    scenario_differences_id = op_json["response"]["scenario_differences"]
    scenario_differences_json = requests_util.get_req("scenario_differences", scenario_differences_id, dev)
    
    try:
        compressor_kw_change = scenario_differences_json["response"]["compressor_peak_kw_change"]
    except:
        compressor_kw_change = 0

    try:
        dryer_kw_change = scenario_differences_json["response"]["dryer_kw_change"]
    except:
        dryer_kw_change = 0

    kw_change = compressor_kw_change 

    new_15_kw = kw_demand_15min + kw_change
    print(f"new_15_kw: {new_15_kw}")
    return new_15_kw

def pressure_difference(pressure, op_json, dev):

    scenario_differences_id = op_json["response"]["scenario_differences"]
    scenario_differences_json = requests_util.get_req("scenario_differences", scenario_differences_id, dev)
    
    try:
        filter_psi_change = scenario_differences_json["response"]["filter_psi_change"]
    except:
        filter_psi_change = 0

    new_pressure = pressure + filter_psi_change
    return new_pressure

def get_peak_15_acfm(op_json, dev):
    peak_15min_acfm = op_json["response"]["peak_15min_acfm"]

    scenario_differences_id = op_json["response"]["scenario_differences"]
    scenario_differences_json = requests_util.get_req("scenario_differences", scenario_differences_id, dev)
    
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

def calculate_row(report_json, demand_schedule_id, op_id, op_json, baseline_operation_7_1, dev, scope):

    # period_data = filter_df(df, report_json, op_id, dev)
    period_data = data_crunch_util.get_op_data_crunch(op_id, dev)
    
    report_id = report_json["response"]["_id"]

    pressure = pressure_util.get_pressure_index(report_id, op_json, dev)

    if scope: # If the scope os not None, it'll be "proposed" or "baseline"
        pressure = pressure_difference(pressure, op_json, dev)

        if op_id == demand_schedule_id:
            kw_demand_15min = get_kw_demand_15min(report_json, op_json, dev)
        else:
            kw_demand_15min = report_json["response"]["kw_max_avg_15"]
        
        peak_15min_acfm = get_peak_15_acfm(op_json, dev)


        try:
            average_acfm = op_json["response"]["ACFM Made"]
            hours_annual = op_json["response"]["Hours/yr"]
            average_kw_demand = op_json["response"]["kW"]

        except:
            print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
            sys.exit(1)


        kwh_annual = average_kw_demand * hours_annual
    else: # Case for running figure in report
        # Average Calcs
        average_acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
        average_kw_demand = period_data.filter(like='Kilowatts').sum(axis=1).mean()

        # Peak 15 min Calcs
        peak_15min_acfm = period_data.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
        kw_demand_15min = period_data.filter(like='Kilowatts').sum(axis=1)[::-1].rolling(window=75, min_periods=75).mean()[::-1].fillna(0).max()
        print(f"kw_demand_15min: {kw_demand_15min}")

        try:
            average_acfm = op_json["response"]["ACFM Made"]
            avg_kw = op_json["response"]["kW"]
            hours_annual = op_json["response"]["Hours/yr"]
        except:
            print(f"Did you already run section 3.2? You need to if you haven't.", file=sys.stderr)
            sys.exit(1)

        kwh_annual = average_kw_demand * hours_annual



    cost_to_operate = financial_util.get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id, op_id, dev)

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

    response = requests_util.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def calculate_dryer_row(report_json, baseline_operation_7_1, kw, kw_demand_15min, dev):
    
    average_kw_demand = kw

    total_hours = report_json["response"]["total_hours"]

    kwh_annual = average_kw_demand * total_hours

    cost_to_operate = financial_util.get_cost_to_operate(report_json, kw_demand_15min, kwh_annual, demand_schedule_id="Dryers", op_id=None, dev=dev)

    label = "Dryers"

    body = {
        "average_kw_demand": average_kw_demand,
        "kw_demand_15min": kw_demand_15min,
        "kwh_annual": kwh_annual,
        "cost_to_operate": cost_to_operate,
        "baseline_operation_7_1": baseline_operation_7_1,
        "label": label
    }

    response = requests_util.post_req("baseline_operation_7_1_row", body, dev)

    print(f"ROW POST REQ RESPONSE: {response}")
    row_id = response["id"]
    
    return row_id

def get_report_dryer_kw(report_json, dev):
    baseline_operation_7_1 = report_json["response"]["baseline_operation_7_1"]
    baseline_operation_7_1_json = requests_util.get_req("baseline_operation_7_1", baseline_operation_7_1, dev)

    baseline_operation_7_1_rows = baseline_operation_7_1_json["response"]["baseline_operation_7_1_row"]

    for row in baseline_operation_7_1_rows:
        row_json = requests_util.get_req("baseline_operation_7_1_row", row, dev)
        label = row_json["response"]["label"]

        if label == "Dryers":
            average_kw_demand = row_json["response"]["average_kw_demand"]
            kw_demand_15min = row_json["response"]["kw_demand_15min"]
            return average_kw_demand, kw_demand_15min
        
def calculate_dryer_scenario(report_json, operation_period_ids, baseline_operation_7_1, dev):
    kw_demand_15min = report_json["response"]["kw_max_avg_15"]

    dryer_kw_changes = []
    dryer_peak_kw_changes = []
    for operation_period_id in operation_period_ids:
        op_json = requests_util.get_req("operation_period", operation_period_id, dev)

        scenario_differences_id = op_json["response"]["scenario_differences"]
        scenario_differences_json = requests_util.get_req("scenario_differences", scenario_differences_id, dev)

        try:
            dryer_kw_change = scenario_differences_json["response"]["dryer_kw_change"]
            dryer_kw_changes.append(dryer_kw_change)
        except:
            print("no dryer_kw_change")

        try:
            dryer_peak_kw_change = scenario_differences_json["response"]["dryer_peak_kw_change"]
            dryer_peak_kw_changes.append(dryer_peak_kw_change)
        except:
            print("no dryer_peak_kw_change")

    try:
        avg_dryer_kw_change = sum(dryer_kw_changes)/len(dryer_kw_changes)
    except:
        avg_dryer_kw_change = 0
    
    try:
        avg_dryer_peak_kw_change = sum(dryer_peak_kw_changes)/len(dryer_peak_kw_changes)
    except:
        avg_dryer_peak_kw_change = 0

    report_dryer_kw, report_dryer_peak_kw = get_report_dryer_kw(report_json, dev)

    new_dryer_kw = report_dryer_kw + avg_dryer_kw_change
    new_dryer_peak_kw = report_dryer_peak_kw + avg_dryer_peak_kw_change

    row_id = calculate_dryer_row(report_json, baseline_operation_7_1, new_dryer_kw, new_dryer_peak_kw, dev)

    return row_id

def calculate_dryer_report(report_json, baseline_operation_7_1, dev):
    try:
        dryer_ids = report_json["response"]["dryer"]
    except:
        print(f"No Dryers?", file=sys.stderr)
        sys.exit(1)

    kws = []
    demand_kws = []

    for dryer_id in dryer_ids:
        dryer_json = requests_util.get_req("dryer", dryer_id, dev)
        try:
            connected_to = dryer_json["response"]["connected_to"]
            full_load_kw = dryer_json["response"]["full_load_kw"]
            demand_kws.append(full_load_kw)
            capacity_scfm = dryer_json["response"]["capacity_scfm"]

            type = dryer_json["response"]["type_if_desiccant_dryer"]
            control = dryer_json["response"]["control"]
        except:
            print(f"Missing some dryer data make sure all the fields are filled out plz", file=sys.stderr)
            sys.exit(1)
        
        ac_ids, ac_idxs = dryers_util.get_ac_ids_for_dryer(report_json, connected_to, dev)

        report_id = report_json["response"]["_id"]

        # Get kW
        if control == "Cycling":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: dryers_util.calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm, dryer_json))
            kw = df["Kilowatts"].mean()

        elif control == "Non-Cycling":
            kw = full_load_kw

        elif control == "Timed":
            kw = dryers_util.timed_kw_calc(dryer_json, full_load_kw)

        elif control == "Dew Point Demand":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"Kilowatts"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: dryers_util.dpd_kw_calc(acfm, full_load_kw, capacity_scfm, dryer_json))
            kw = df["Kilowatts"].mean()

        kws.append(kw)
        
        # get cfm_loss
        if control == "Dew Point Demand":
            # df = get_cfm_df(report_json, ac_ids, dev)
            df = data_crunch_util.get_report_data_crunch(report_id, "data_crunch_trim_exclu", dev)
            df = data_crunch_util.filter_df_to_ac_idx(df, ac_idxs)
            df[f"CFM Loss"] = df.filter(like='ACFM').sum(axis=1).apply(lambda acfm: dryers_util.get_cfm_loss_dpd(acfm, capacity_scfm, type))
            cfm_loss = df["CFM Loss"].mean()
        else:
            cfm_loss = dryers_util.get_dryer_cfm_loss(capacity_scfm, type)
        
        requests_util.patch_req("dryer", dryer_id, body={"scfm_dryer_loss": cfm_loss}, dev=dev)

    total_kw = sum(kws)

    total_demand_kw = sum(demand_kws)

    row_id = calculate_dryer_row(report_json, baseline_operation_7_1, total_kw, total_demand_kw, dev)

    return row_id


def start_calculations(operation_period_ids, demand_schedule_id, report_json, baseline_operation_7_1, dev, scope=None):

    # df = df_calcs(report_json, dev)

    row_ids = []

    for operation_period_id in operation_period_ids:
        print(f"OP ID: {operation_period_id}")
        op_json = requests_util.get_req("operation_period", operation_period_id, dev)
        
        row_id = calculate_row(report_json, demand_schedule_id, operation_period_id, op_json, baseline_operation_7_1, dev, scope)
        row_ids.append(row_id)

    if scope:
        row_id = calculate_dryer_scenario(report_json, operation_period_ids, baseline_operation_7_1, dev)
    else:
        row_id = calculate_dryer_report(report_json, baseline_operation_7_1, dev)
    row_ids.append(row_id)

    patch_response = requests_util.patch_req("baseline_operation_7_1", baseline_operation_7_1, body={"baseline_operation_7_1_row": row_ids}, dev=dev)
    # print(f"PATCH REQ RESPONSE: {patch_response}")






