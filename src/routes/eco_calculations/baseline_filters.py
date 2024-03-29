import os
import sys
import json
import baseline_global

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

# Returns a list of filter ids that are attached to the current air compressor.
def get_report_filters(r_ac_name, report_json, dev):
    r_f_ids = report_json["response"]["filter"]

    ac_r_f_ids = []
    for r_f_id in r_f_ids:
        r_f_json = common_functions.get_req("filter", r_f_id, dev)
        connected_to = r_f_json["response"]["connected_to"]
        connected_to_list = connected_to.split(", ")
        if r_ac_name in connected_to_list:
            ac_r_f_ids.append(r_f_id)

    return ac_r_f_ids

def get_filter_psis(f_ids, dev):
    peak_psis = []
    avg_psis = []

    for f_id in f_ids:
        f_json = common_functions.get_req("filter", f_id, dev)
        peak_psi = f_json["response"]["peak_psig_drop"]
        peak_psis.append(peak_psi)

        avg_psig_drop = f_json["response"]["psig_drop"]
        avg_psis.append(avg_psig_drop)
    
    return sum(avg_psis), sum(peak_psis)


def get_baseline_filters(r_ac_name, scenario_id, dev):
    s_json = common_functions.get_req("scenario", scenario_id, dev)
    s_baseline_id = s_json["response"]["scenario_baseline"]
    s_baseline_json = common_functions.get_req("scenario_baseline", s_baseline_id, dev)
    s_f_ids = s_baseline_json["response"]["filter"]

    ac_s_f_ids = []
    for s_f_id in s_f_ids:
        s_f_json = common_functions.get_req("filter", s_f_id, dev)
        connected_to = s_f_json["response"]["connected_to"]
        connected_to_list = connected_to.split(", ")
        if r_ac_name in connected_to_list:
            ac_s_f_ids.append(s_f_id)

    return ac_s_f_ids


def start():
    dev, report_id, scenario_id = get_payload()

    report_json = common_functions.get_req("report", report_id, dev)

    r_ac_ids = report_json["response"]["air_compressor"]

    # I don't think it needs to be per operating period because it should be the same difference between each operating period.
    # For each compressor
    for r_ac_id in r_ac_ids:

        # Get Compressor Name
        r_ac_json = common_functions.get_req("air_compressor", r_ac_id, dev)
        r_ac_name = r_ac_json["response"]["Customer CA"]
        print("")
        print(f"Compressor: {r_ac_name}")

        # Get Report Filters
        r_f_ids = get_report_filters(r_ac_name, report_json, dev)
        print(f"r_f_ids: {r_f_ids}")

        # PSI drop in Report (avg & peak)
        r_avg_psi, r_peak_psi = get_filter_psis(r_f_ids, dev)
        print(f"Report avg psi drop: {r_avg_psi}, Report peak psi drop: {r_peak_psi}")

        # Get baseline Filters
        s_f_ids = get_baseline_filters(r_ac_name, scenario_id, dev)
        print(f"s_f_ids: {s_f_ids}")

        # PSI in baseline (avg & peak)
        s_avg_psi, s_peak_psi = get_filter_psis(s_f_ids, dev)
        print(f"baseline avg psi drop: {s_avg_psi}, baseline peak psi drop: {s_peak_psi}")

        # baseline PSI Differences (avg & peak)
        print(f"PSI Differences!")
        print(f"Compressor: {r_ac_name}, avg psi difference: {s_avg_psi - r_avg_psi}, peak psi difference: {s_peak_psi - r_peak_psi}")
        print("")
start()
