import sys
import json
from datetime import datetime, timedelta
import os
import proposed_7_1

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

def delete_datasets_7_2(report_id, operation_period_ids, dev):
    for operation_period_id in operation_period_ids:
        operation_json = common_functions.get_req("operation_period", operation_period_id, dev)
        if "Name" in operation_json["response"]:    
            op_name =  operation_json["response"]["Name"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": "Forgot to Name your Operating Period", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        if "dataset_7_2" in operation_json["response"] and operation_json["response"]["dataset_7_2"] != []:
            dataset_7_2_ids = operation_json["response"]["dataset_7_2"]
            for dataset_7_2_id in dataset_7_2_ids:
                common_functions.del_req("dataset_7_2", dataset_7_2_id, dev)
            print(f"Datasets have been deleted in {op_name}")
        else:
            print(f"nothing to delete in {op_name}")

def add_datasets_to_operating_periods(report_id, operation_period_ids, air_compressor_ids, dev):
    for operation_period_id in operation_period_ids: # Loop through each Operating Period

        dataset_ids = []
        for air_compressor_id in air_compressor_ids: # For each operating period, loop through each Air Compressor
            
            # Get the Model from this Air Compressor
            air_compressor_json = common_functions.get_req("air_compressor", air_compressor_id, dev)
            if "Customer CA" in air_compressor_json["response"]:
                ac_name = air_compressor_json["response"]["Customer CA"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {air_compressor_id}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
            
            if "Control Type" in air_compressor_json["response"]:    
                control = air_compressor_json["response"]["Control Type"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Control Type on Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()

            if "Model" in air_compressor_json["response"]:    
                model = air_compressor_json["response"]["Model"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Model Number on Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()

            if "Make" in air_compressor_json["response"]:    
                make = air_compressor_json["response"]["Make"]
            else:
                common_functions.patch_req("Report", report_id, body={"loading": f"Missing Model Number on Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
                sys.exit()
            
            dataset_body = {"Model": model, "operation_period": operation_period_id, "control-type": control, "air_compressor": air_compressor_id, "make": make, "ac_number": ac_name}

            # Create new dataset_7_2 thing and assign this air compressors model to it's model
            response = common_functions.post_req("dataset_7_2", dataset_body, dev)

            # get the id for the newly created dataset_7_2 and add to array for each compressor
            dataset_id = response["id"]
            dataset_ids.append(dataset_id)

        # for each Operation Period, assign the newly created datasets to it
        operation_body = {"dataset_7_2": dataset_ids}

        common_functions.patch_req("operation_period", operation_period_id, operation_body, dev)

def start():
    dev, report_id, scenario_id = get_payload()

    scenario_json = common_functions.get_req("scenario", scenario_id, dev)
    scenario_proposed_id = scenario_json["response"]["scenario_proposed"]

    scenario_proposed_json = common_functions.get_req("scenario_proposed", scenario_proposed_id, dev)
    operation_period_ids = scenario_proposed_json["response"]["operation_period"]
    air_compressor_ids = scenario_proposed_json["response"]["air_compressor"]
    
    common_functions.patch_req("Report", report_id, body={"loading": "Deleting the chart data incase Air Compressors or Operating Periods have changed...", "is_loading_error": "no"}, dev=dev)
    delete_datasets_7_2(report_id, operation_period_ids, dev)

    common_functions.patch_req("Report", report_id, body={"loading": "Recreating empty charts...", "is_loading_error": "no"}, dev=dev)
    add_datasets_to_operating_periods(report_id, operation_period_ids, air_compressor_ids, dev)




start()