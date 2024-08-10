import os
import sys
import json
from eco_calculation import proposed_global
from utilities import requests_util

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

def create_new_scenario_difference(op_id, dev):
    response = requests_util.post_req("scenario_differences", body={"operation_period": op_id}, dev=dev)

    scenario_difference = response["id"]

    requests_util.patch_req("operation_period", op_id, body={"scenario_differences": scenario_difference}, dev=dev)

    return scenario_difference

def get_total_report_filter_psi_drop(report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    filter_ids = report_json["response"]["filter"]

    psi_drops = []
    for filter_id in filter_ids:
        filter_json = requests_util.get_req("filter", filter_id, dev)
        psi_drop = filter_json["response"]["psig_drop"]

        psi_drops.append(psi_drop)

    total_psi_drop = sum(psi_drops)

    return total_psi_drop

def get_avg_proposed_filter_psi_drop(scenario_id, dev):
    scenario_json = requests_util.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = requests_util.get_req("scenario_proposed", scenario_proposed_id, dev)
    filter_ids = scenario_proposed_json["response"]["filter"]

    psi_drops = []
    for filter_id in filter_ids:
        filter_json = requests_util.get_req("filter", filter_id, dev)
        psi_drop = filter_json["response"]["psig_drop"]

        psi_drops.append(psi_drop)
    
    total_proposed_filter_psi_drop = sum(psi_drops)

    return total_proposed_filter_psi_drop

def get_op_ids(scenario_id, dev):
    scenario_json = requests_util.get_req("scenario", scenario_id, dev)

    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = requests_util.get_req("scenario_proposed", scenario_proposed_id, dev)

    operating_period_ids = scenario_proposed_json["response"]["operation_period"]

    return operating_period_ids

# Returns a list of filter ids that are attached to the current air compressor.
def get_report_filters(r_ac_name, report_json, dev):
    r_f_ids = report_json["response"]["filter"]

    ac_r_f_ids = []
    for r_f_id in r_f_ids:
        r_f_json = requests_util.get_req("filter", r_f_id, dev)
        connected_to = r_f_json["response"]["connected_to"]
        connected_to_list = connected_to.split(", ")
        if r_ac_name in connected_to_list:
            ac_r_f_ids.append(r_f_id)

    return ac_r_f_ids

def get_filter_psis(f_ids, dev):
    peak_psis = []
    avg_psis = []

    for f_id in f_ids:
        f_json = requests_util.get_req("filter", f_id, dev)
        peak_psi = f_json["response"]["peak_psig_drop"]
        peak_psis.append(peak_psi)

        avg_psig_drop = f_json["response"]["psig_drop"]
        avg_psis.append(avg_psig_drop)
    
    return sum(avg_psis), sum(peak_psis)


def get_proposed_filters(r_ac_name, scenario_id, dev):
    s_json = requests_util.get_req("scenario", scenario_id, dev)
    s_proposed_id = s_json["response"]["scenario_proposed"]
    s_proposed_json = requests_util.get_req("scenario_proposed", s_proposed_id, dev)
    s_f_ids = s_proposed_json["response"]["filter"]

    ac_s_f_ids = []
    for s_f_id in s_f_ids:
        s_f_json = requests_util.get_req("filter", s_f_id, dev)
        connected_to = s_f_json["response"]["connected_to"]
        connected_to_list = connected_to.split(", ")
        if r_ac_name in connected_to_list:
            ac_s_f_ids.append(s_f_id)

    return ac_s_f_ids


def start():
    dev, report_id, scenario_id = get_payload()

    report_json = requests_util.get_req("report", report_id, dev)

    r_ac_ids = report_json["response"]["air_compressor"]

    # I don't think it needs to be per operating period because it should be the same difference between each operating period.
    # For each compressor
    for r_ac_id in r_ac_ids:

        # Get Compressor Name
        r_ac_json = requests_util.get_req("air_compressor", r_ac_id, dev)
        r_ac_name = r_ac_json["response"]["Customer CA"]
        print("")
        print(f"Compressor: {r_ac_name}")

        # Get Report Filters
        r_f_ids = get_report_filters(r_ac_name, report_json, dev)
        print(f"r_f_ids: {r_f_ids}")

        # PSI drop in Report (avg & peak)
        r_avg_psi, r_peak_psi = get_filter_psis(r_f_ids, dev)
        print(f"Report avg psi drop: {r_avg_psi}, Report peak psi drop: {r_peak_psi}")

        # Get Proposed Filters
        s_f_ids = get_proposed_filters(r_ac_name, scenario_id, dev)
        print(f"s_f_ids: {s_f_ids}")

        # PSI in Proposed (avg & peak)
        s_avg_psi, s_peak_psi = get_filter_psis(s_f_ids, dev)
        print(f"Proposed avg psi drop: {s_avg_psi}, Proposed peak psi drop: {s_peak_psi}")

        # Proposed PSI Differences (avg & peak)
        print(f"PSI Differences!")
        print(f"Compressor: {r_ac_name}, avg psi difference: {s_avg_psi - r_avg_psi}, peak psi difference: {s_peak_psi - r_peak_psi}")
        print("")
    
    # total_proposed_filter_psi_drop = get_total_proposed_filter_psi_drop(scenario_id, dev)
    # total_report_filter_psi_drop = get_total_report_filter_psi_drop(report_id, dev)

    # total_filter_psi_drop = total_proposed_filter_psi_drop - total_report_filter_psi_drop

    # operating_period_ids = get_op_ids(scenario_id, dev)

    # for operating_period_id in operating_period_ids:
    #     operating_period_json = requests_util.get_req("operation_period", operating_period_id, dev)
    #     try:
    #         scenario_differences = operating_period_json["response"]["scenario_differences"]
    #     except:
    #         scenario_differences = create_new_scenario_difference(operating_period_id, dev)

    #     requests_util.patch_req("scenario_differences", scenario_differences, body={"filter_psi_change": total_filter_psi_drop}, dev=dev)

    #     proposed_global.update_op_stats(operating_period_id, report_id, dev)


if __name__ == "__main__":
    start()
