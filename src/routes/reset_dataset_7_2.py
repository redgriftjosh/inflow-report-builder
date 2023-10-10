import sys
import json
import requests
import common_functions

def start(report_id, report_json, dev):
    if "Operation Period" in report_json["response"] and report_json["response"]["Operation Period"] != []:
        operation_period_ids = report_json["response"]["Operation Period"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operation Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    if "Air Compressor" in report_json["response"] and report_json["response"]["Air Compressor"] != []:
        air_compressor_ids = report_json["response"]["Air Compressor"]
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Air Compressors Found! You need at least one Air Compressor.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    
    common_functions.patch_req("Report", report_id, body={"loading": "Deleting the chart data incase Air Compressors or Operating Periods have changed...", "is_loading_error": "no"}, dev=dev)
    delete_datasets_7_2(report_id, operation_period_ids, dev)

    common_functions.patch_req("Report", report_id, body={"loading": "Recreating empty charts...", "is_loading_error": "no"}, dev=dev)
    add_datasets_to_operating_periods(operation_period_ids, air_compressor_ids, dev)


def delete_datasets_7_2(report_id, operation_period_ids, dev):
    for operation_period_id in operation_period_ids:
        operation_json = common_functions.get_req("Operation-Period", operation_period_id, dev)
        if "Name" in operation_json["response"]:    
            op_name =  operation_json["response"]["Name"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": "Forgot to Name your Operating Period", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        if "dataset-7-2" in operation_json["response"] and operation_json["response"]["dataset-7-2"] != []:
            dataset_7_2_ids = operation_json["response"]["dataset-7-2"]
            for dataset_7_2_id in dataset_7_2_ids:
                common_functions.del_req("dataset-7-2", dataset_7_2_id, dev)
            print(f"Datasets have been deleted in {op_name}")
        else:
            print(f"nothing to delete in {op_name}")


def add_datasets_to_operating_periods(operation_period_ids, air_compressor_ids, dev):
    for operation_period_id in operation_period_ids: # Loop through each Operating Period

        dataset_ids = []
        for air_compressor_id in air_compressor_ids: # For each operating period, loop through each Air Compressor
            
            # Get the Model from this Air Compressor
            air_compressor_json = common_functions.get_req("Air-Compressor", air_compressor_id, dev)
            model = air_compressor_json["response"]["Model"]
            control = air_compressor_json["response"]["Control Type"]
            dataset_body = {"Model": model, "operating-period": operation_period_id, "control-type": control, "air-compressor": air_compressor_id}

            # Create new dataset_7_2 thing and assign this air compressors model to it's model
            response = common_functions.post_req("dataset-7-2", dataset_body, dev)

            # get the id for the newly created dataset_7_2 and add to array for each compressor
            dataset_id = response["id"]
            dataset_ids.append(dataset_id)

        # for each Operation Period, assign the newly created datasets to it
        operation_body = {"dataset-7-2": dataset_ids}

        common_functions.patch_req("Operation-Period", operation_period_id, operation_body, dev)

