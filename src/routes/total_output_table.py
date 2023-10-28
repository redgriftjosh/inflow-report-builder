import common_functions
import sys
import json
import csv
import base64
import pandas as pd
import requests

def get_things(my_json, report_id, processed_ids, iteration, total_output, dev):
    # take the report_json with only objects e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
    iteration += 1
    # for each object attached to the report... e.g. 'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021']
    for key, value in my_json.items():

        try:
            common_functions.patch_req("report", report_id, body={'loading': f"Getting Values from: {key}", "is_loading_error": "no"}, dev=dev)
        except:
            print(f"Could not update loading text: {key}")
        # Check if the value is an array e.g. ['12398467x219083473243224', '10843759387x0293481029374021']
        if isinstance(value, list):
            new_ids = []
            # For each id in the list...
            for id in value:

                # add this object id to the list of processed ids
                processed_ids.append(id)

                # Get the json for that object id
                my_thing = common_functions.get_req(key, id, dev) # Will only work if all things are named the same as they're referenced
                # print(f"get_things - {iteration}: {my_thing}")
                # print('')
                
                my_thing = common_functions.clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
                total_output.update({f"{key}_{id}": my_thing})
                # print(f"Getting Things - {iteration} - cleaned_json and added to list: {my_thing}")
                # print(f"total_output so far: {total_output}")
                # print('')

                things_json = common_functions.find_ids(my_thing) # check to see if there are any ids attached to this thing
                # print(f"Getting Things - {iteration} - find_ids: {things_json}")
                # print('')
                
                # if there are things attached to this thing
                if things_json:
                    print(f"moving onto get_things - {iteration+1}")
                    total_output = get_things(things_json, report_id, processed_ids, iteration, total_output, dev)
                else:
                    print('No more things to get here')
                    print('')
                print('')
        
        # if it's not an array e.g. 'trim': '098732490873x298374210398701'
        else:

            processed_ids.append(value)

            # Get the json for that object id
            my_thing = common_functions.get_req(key, value, dev) # Will only work if all things are named the same as they're referenced
            # print(f"get_things - {iteration}: {my_thing}")
            # print('')
            
            my_thing = common_functions.clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
            total_output.update({f"{key}_{value}": my_thing})
            # print(f"Getting Things - {iteration} - cleaned_json and added to list: {my_thing}")
            # print('')

            things_json = common_functions.find_ids(my_thing) # check to see if there are any ids attached to this thing
            # print(f"Getting Things - {iteration} - find_ids: {things_json}")
            # print('')
            
            # if there are things attached to this thing
            if things_json:
                print(f"moving onto get_things - {iteration+1}")
                total_output = get_things(things_json, report_id, processed_ids, iteration, total_output, dev)
            else:
                print('No more things to get here')
                print('')
            print('')
    return total_output

def remove_keys(my_dict, keys_to_remove, is_top_level=True):
    if not isinstance(my_dict, dict):
        return my_dict

    cleaned_data = {}
    for key, value in my_dict.items():
        if key not in keys_to_remove or (key in keys_to_remove and is_top_level):
            cleaned_data[key] = remove_keys(value, keys_to_remove, is_top_level=False)

    return cleaned_data

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this

    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    processed_ids = []
    report_id = data.get('report-id')

    processed_ids.append(report_id)

    total_output = {}

    iteration = 0

    report_json = common_functions.get_req("report", report_id, dev)

    # print(f"1 - Dirty Report Json: {report_json}")
    # print('')
    try:
        report_json = common_functions.clean_json(report_json, processed_ids)
        total_output.update({"report": report_json})
        # print(f"1 - Cleaned Report Json & Added to Total Output: {report_json}")
        # print('')
    except:
        common_functions.patch_req("report", report_id, body={'loading': f"trouble cleaning report_json (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    try:
        things_json = common_functions.find_ids(report_json) # returns the report_json but only with thing ids e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
        # print(f"1 - ONLY IDS: {things_json}")
        # print('')
    except:
        common_functions.patch_req("report", report_id, body={'loading': f"trouble with find_ids (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if things_json:
        total_output = get_things(things_json, report_id, processed_ids, iteration, total_output, dev) # should return a completed dictionary of every key: value in this report

    keys_to_remove = ['acfm-graph-3-min', 'air_compressor', 'created_by_user_id', 'electrical_provider', 'exclusion', 'Google Sheets Spreadsheet ID', 'is_loading_error', 'loading', 'updating', 'report', 'vfd_slope_entries', 'pressure_sensor', 'operation_period', 'dataset_7_2', 'file', 'logger_graph', 'ac_data_logger', 'logger-html', 'logger-image', 'electrical_provider_entry', 'collapsed', 'pressure-html', 'histogram_html']
    total_output = remove_keys(total_output, keys_to_remove)
    # Specify the CSV file name
    # csv_file = 'total_output_table.csv'


    # Open the CSV file in write mode
    # with open(csv_file, 'w',newline='') as file:
    #     writer = csv.writer(file)
        
    #     # Write the header row
    #     writer.writerow(['Key', 'Value'])
        
    #     # Write the data rows
    #     for key, value in total_output.items():
    #         writer.writerow([key, value])

    # print(f'Dictionary has been converted to {csv_file}')

    # csv_data = pd.read_csv(csv_file)

    rows = []
    for outer_key, inner_dict in total_output.items():
        rows.append([outer_key, None, None])  # Adding the primary row
        for inner_key, value in inner_dict.items():
            rows.append([None, inner_key, value])  # Adding the sub-rows
        rows.append([None, None, None])  # Adding a blank row for separation

    # Convert rows to a DataFrame
    df = pd.DataFrame(rows, columns=['Categories', 'Variable Name', 'Value'])

    csv_string = df.to_csv(index=False)

    base64_encoded_data = base64.b64encode(csv_string.encode()).decode()

    body = {
        "total_output_table": {
            "filename": "total_output_table.csv",
            "contents": base64_encoded_data,
            "private": False
            }
        }

    url = f"https://inflow-co.bubbleapps.io{dev}/api/1.1/obj/report/{report_id}"

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1"
    }

    try:
        response = requests.patch(url, json=body, headers=headers)
        print(f"patched: total_output_table.csv, {response.status_code}")
        print(response.text)
    except requests.RequestException as e:
        print(e)
    
    common_functions.patch_req("report", report_id, body={'loading': f"Success!", "is_loading_error": "no"}, dev=dev)

start()
