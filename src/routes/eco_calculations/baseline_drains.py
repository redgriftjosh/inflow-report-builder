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

def create_new_scenario_difference(op_id, dev):
    response = common_functions.post_req("scenario_differences", body={"operation_period": op_id}, dev=dev)

    scenario_difference = response["id"]

    common_functions.patch_req("operation_period", op_id, body={"scenario_differences": scenario_difference}, dev=dev)

    return scenario_difference

def get_total_report_drain_cfm(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    drain_ids = report_json["response"]["drain"]

    adjusted_cfms = []
    for drain_id in drain_ids:
        drain_json = common_functions.get_req("drain", drain_id, dev)

        try:
            off_min = drain_json["response"]["baseline_off_min"]
            on_sec = drain_json["response"]["baseline_on_sec"]
        except:
            off_min = 0
            on_sec = 0
        

        if off_min == 0 or on_sec == 0:
            try:
                adjusted_cfm = drain_json["response"]["acfm_loss"]
                
            except:
                adjusted_cfm = 0

        else:

            try:
                cycles_per_hour = 0 if off_min < 0.1 else 60 / off_min

                cf_per_cycle = on_sec * (52 / 60) # Currently hard coding 52 CFM can get through the drain

                try:
                    acfm_loss = drain_json["response"]["acfm_loss"]
                except:
                    acfm_loss = 0

                adjusted_cfm = acfm_loss + (cycles_per_hour * cf_per_cycle / 60)

            except:
                adjusted_cfm = 0
        

        adjusted_cfms.append(adjusted_cfm)

    total_report_drain_cfm = sum(adjusted_cfms)

    return total_report_drain_cfm

def get_total_baseline_drain_cfm(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_baseline_id = scenario_json["response"]["scenario_baseline"]

    scenario_baseline_json = common_functions.get_req("scenario_baseline", scenario_baseline_id, dev)
    drain_ids = scenario_baseline_json["response"]["drain"]

    adjusted_cfms = []
    for drain_id in drain_ids:
        drain_json = common_functions.get_req("drain", drain_id, dev)

        try:
            off_min = drain_json["response"]["baseline_off_min"]
            on_sec = drain_json["response"]["baseline_on_sec"]
        except:
            off_min = 0
            on_sec = 0
        

        if off_min == 0 or on_sec == 0:
            try:
                adjusted_cfm = drain_json["response"]["acfm_loss"]
                
            except:
                adjusted_cfm = 0

        else:

            try:
                cycles_per_hour = 0 if off_min < 0.1 else 60 / off_min

                cf_per_cycle = on_sec * (52 / 60) # Currently hard coding 52 CFM can get through the drain

                try:
                    acfm_loss = drain_json["response"]["acfm_loss"]
                except:
                    acfm_loss = 0

                adjusted_cfm = acfm_loss + (cycles_per_hour * cf_per_cycle / 60)

            except:
                adjusted_cfm = 0
        

        adjusted_cfms.append(adjusted_cfm)
    
    total_baseline_drain_cfm = sum(adjusted_cfms)

    return total_baseline_drain_cfm

def get_op_ids(scenario_id, dev):
    scenario_json = common_functions.get_req("scenario", scenario_id, dev)

    scenario_baseline_id = scenario_json["response"]["scenario_baseline"]

    scenario_baseline_json = common_functions.get_req("scenario_baseline", scenario_baseline_id, dev)

    operating_period_ids = scenario_baseline_json["response"]["operation_period"]

    return operating_period_ids

def start():
    dev, report_id, scenario_id = get_payload()
    
    total_baseline_drain_cfm = get_total_baseline_drain_cfm(scenario_id, dev)
    total_report_drain_cfm = get_total_report_drain_cfm(report_id, dev)

    total_drain_cfm = total_baseline_drain_cfm - total_report_drain_cfm

    operating_period_ids = get_op_ids(scenario_id, dev)

    for operating_period_id in operating_period_ids:
        operating_period_json = common_functions.get_req("operation_period", operating_period_id, dev)
        try:
            scenario_differences = operating_period_json["response"]["scenario_differences"]
        except:
            scenario_differences = create_new_scenario_difference(operating_period_id, dev)

        common_functions.patch_req("scenario_differences", scenario_differences, body={"drain_cfm_change": total_drain_cfm}, dev=dev)

        baseline_global.update_op_stats(operating_period_id, report_id, dev)


start()
