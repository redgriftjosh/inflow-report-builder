import sys
import json
import common_functions

def get_dependencies(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    peak_acfm_15min = report_json["response"]["15 Min Peak Flow"]
    kw_max_avg_15 = report_json["response"]["kw_max_avg_15"]
    total_op_hours = common_functions.get_total_annual_operating_hours(report_json, dev)

    return peak_acfm_15min, kw_max_avg_15, total_op_hours

def get_body(installed_total, incremental_total, kw_demand_total, kwh_per_year_total, o_and_m_total, dollars_per_year_total, incentive_total, payback_years_total):
    body = {
        "installed": installed_total,
        "incremental": incremental_total,
        "kw_demand": kw_demand_total,
        "kw_max": kw_demand_total,
        "kwh_per_year": kwh_per_year_total,
        "dollars_per_year": dollars_per_year_total,
        "incentive_estimate": incentive_total,
        "percent_or_o_and_m": o_and_m_total,
        "payback_years": payback_years_total
    }

    return body

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

    return dev, report_id

def get_incremental(installed, eco_table_8_1_drain_input_json):
    base_installed_cost = eco_table_8_1_drain_input_json["response"]["base_installed_cost"]

    incremental = installed - base_installed_cost

    return incremental

def get_drain_selection_ids(eco_table_8_1_drain_input_json, report_id, dev):
    drain_selection_string = eco_table_8_1_drain_input_json["response"]["drain_selection"]

    drain_selection_list = drain_selection_string.split(", ")

    report_json = common_functions.get_req("report", report_id, dev)

    drains = report_json["response"]["drain"]

    selected_drain_ids = []

    for drain in drains:
        drain_json = common_functions.get_req("drain", drain, dev)
        drain_number = drain_json["response"]["drain_number"]
        
        if drain_number in drain_selection_list:
            selected_drain_ids.append(drain)

    return selected_drain_ids

def get_o_and_m(eco_table_8_1_drain_input_json):
    operating_costs = eco_table_8_1_drain_input_json["response"]["operating_costs"]
    maintenance_costs = eco_table_8_1_drain_input_json["response"]["maintenance_costs"]

    return operating_costs + maintenance_costs

def calculate_row(drain_selection_ids, peak_acfm_15min, kw_max_avg_15, eco_table_8_1_drain_input_json, total_op_hours, report_id, dev):
    kw_demand_list = []
    kwh_per_year_list = []
    dollars_per_year_list = []

    for drain_selection_id in drain_selection_ids:
        drain_json = common_functions.get_req("drain", drain_selection_id, dev)
        acfm_loss = drain_json["response"]["acfm_loss"]

        # Calculate kW Max & kW Demand
        kw_demand = acfm_loss * kw_max_avg_15 / peak_acfm_15min
        kw_demand_list.append(kw_demand)

        # Calculate the amount of kWh/yr spent on this drain
        kwh_per_year = kw_demand * total_op_hours
        kwh_per_year_list.append(kwh_per_year)

        # Calculates dollars spent per year on this drain
        dollars_per_year = common_functions.get_cost_to_operate(report_id, kw_demand, kwh_per_year, dev)
        dollars_per_year_list.append(dollars_per_year)
    
    installed_total = eco_table_8_1_drain_input_json["response"]["installed_cost"]
    incremental_total = get_incremental(installed_total, eco_table_8_1_drain_input_json)
    kw_demand_total = sum(kw_demand_list)
    kwh_per_year_total = sum(kwh_per_year_list)
    o_and_m_total = get_o_and_m(eco_table_8_1_drain_input_json)
    dollars_per_year_total = sum(dollars_per_year_list)

    # Incentive that was entered by the user.
    incentive_total = eco_table_8_1_drain_input_json["response"]["incentive"]

    # Payback years
    try:
        payback_years_total = (incremental_total - incentive_total) / (dollars_per_year_total + o_and_m_total)
    except:
        payback_years_total = 1234

    body = get_body(installed_total, incremental_total, kw_demand_total, kwh_per_year_total, o_and_m_total, dollars_per_year_total, incentive_total, payback_years_total)

    eco_table_8_1_id = eco_table_8_1_drain_input_json["response"]["eco_table_8_1"]
    common_functions.patch_req("eco_table_8_1", eco_table_8_1_id, body, dev)

def start_calculations(peak_acfm_15min, kw_max_avg_15, total_op_hours, dev, report_id):
    report_json = common_functions.get_req("report", report_id, dev) # For retrieving dependencies

    eco_table_8_1_drain_input_ids = report_json["response"]["eco_table_8_1_drain_input"]

    for eco_table_8_1_drain_input_id in eco_table_8_1_drain_input_ids:
        eco_table_8_1_drain_input_json = common_functions.get_req("eco_table_8_1_drain_input", eco_table_8_1_drain_input_id, dev)

        drain_selection_ids = get_drain_selection_ids(eco_table_8_1_drain_input_json, report_id, dev)
        print(f"drain_selection_ids: {drain_selection_ids}")

        calculate_row(drain_selection_ids, peak_acfm_15min, kw_max_avg_15, eco_table_8_1_drain_input_json, total_op_hours, report_id, dev)

def start():
    # Get variables in payload
    dev, report_id = get_payload()

    # Gets all the dependencies not included in payload
    peak_acfm_15min, kw_max_avg_15, total_op_hours = get_dependencies(report_id, dev)
    # print(f"peak_acfm_15min: {peak_acfm_15min}")
    # print(f"kw_max_avg_15: {kw_max_avg_15}")
    # print(f"total_op_hours: {total_op_hours}")

    # For each row qualified as a drain
    start_calculations(peak_acfm_15min, kw_max_avg_15, total_op_hours, dev, report_id)

start()