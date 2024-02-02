import sys
import json
import common_functions
import re

# This script creates a duplacate of the report for a proposed scenario as well as a baseline scenario so the user can make modifications and get numbers for section 8.1

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
    
    report_json = common_functions.get_req("report", report_id, dev)

    try:
        created_by_user_id = report_json["response"]["Created By"]
    except:
        created_by_user_id = report_json["response"]["created_by_user_id"]

    


    return dev, report_id, scenario_id, created_by_user_id

def create_proposed(dev, report_id, scenario_id):
    common_functions.post_req("scenario_proposed", body={})

def get_compressors(dev, report_id):
    report_json = common_functions.get_req("report", report_id, dev)
    compressor_ids = report_json["response"]["air_compressor"]
    
def clean_json(my_json, processed_ids):
    my_json = my_json['response']
    keys_to_remove = [
        "_id", 
        "Modified Date", 
        "Created Date", 
        "Created By", 
        "created_by_user_id", 
        "ac_data_logger", 
        "client_info",
        "demand_usage_info_6",
        "download_link",
        "eco",
        "eco_table_8_1",
        "eco_table_8_1_drain_input",
        "electrical_provider",
        "electrical_provider_entry",
        "exclusion",
        "global",
        "goal",
        "leak_detection_ultra_sonic_6_1",
        "logger_graph",
        "Mytable",
        "pressure_sensor",
        "scenario",
        "scenario_baseline",
        "scenario_end_values",
        "scenario_proposed",
        "scenario_differences",
        "section_5_2",
        "section_5_1",
        "section_5",
        "trim"
        ]

    for key in keys_to_remove:
        print(f"Removed: {key}")
        my_json.pop(key, None)

    new_json = {}

    for key, value in my_json.items():
        if value not in processed_ids:
            new_json[key] = value
        else:
            print(f"Removed: {key}: {value}")
            
    print('')
    return new_json

def find_ids(my_json):
    object_id_pattern = re.compile(r'^\d+x\d+$') # pattern states any number of numbers separated by an x e.g.(1x1) or (12423x0934)
    id_dict = {}
    for key, value in my_json.items(): # For each item in the clean json (should be clean)
        if isinstance(value, list): # if the value of this item is an array (LiSt)
            for id in value: # for each id in the list
                if object_id_pattern.match(str(id)) and len(str(id)) == 32: # if it matches pattern and is 32 characters add to dict
                    id_dict[key] = value
                break
        else:
            if object_id_pattern.match(str(value)) and len(str(value)) == 32: # if it's not a list then just check if the value matches and add to dictionary
                id_dict[key] = value

    
    return id_dict

def update_new_things(new_thing_id, new_type, new_things_json, dev):

    for key, value in new_things_json.items():

        if isinstance(value, list):

            for id in value:
                common_functions.patch_req(key, str(id), body={new_type: new_thing_id}, dev=dev)
        else:
            common_functions.patch_req(key, str(value), body={new_type: new_thing_id}, dev=dev)

def get_new_things(my_json, created_by_user_id, processed_ids, iteration, dev):
    print(f"get_new_things - iteration: {iteration}")
    iteration += 1
    # take the report_json with only objects e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
    new_things = {}

    # for each object attached to the report... e.g. 'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021']
    for key, value in my_json.items():
        try:
            common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"Copying: {key}", "is_loading_error": "no"}, dev=dev)
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
                try:
                    my_thing = common_functions.get_req(key, id, dev) # Will only work if all things are named the same as they're referenced
                    # print(f"get_new_things_{iteration}: {json.dumps(my_thing)[:1000]}")
                    # print('')
                except:
                    try:
                        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"Error: Could not find item: {key}. Please tell Josh to check the database for spelling mistakes.", "is_loading_error": "yes"}, dev=dev)
                    except:
                        print(f"Could not update loading text: {key}")

                
                my_thing = clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
                # print(f"get_new_things_{iteration} - clean_json: {my_thing}")
                # print('')

                things_json = find_ids(my_thing) # check to see if there are any ids attached to this thing
                # print(f"get_new_things_{iteration} - find_ids: {things_json}")
                # print('')
                
                # if there are things attached to this thing
                if things_json:
                    print(f"moving onto get_new_things_{iteration+1}")
                    new_things_json = get_new_things(things_json, created_by_user_id, processed_ids, iteration, dev) # returns a json with the new ids formatted the same as above but with each object copied and a new id assigned.
                    for new_key in new_things_json:
                        my_thing[new_key] = new_things_json[new_key]
                else:
                    print('No more things to create here')
                    print('')
                

                response = common_functions.post_req(key, my_thing, dev) # Create new object with the same json in the one we just got
                # print(f"get_new_things_{iteration} - post_req: {response}")
                # print('')
                # print('')

                new_id = response['id'] # Get the new id
                if things_json:
                    update_new_things(new_id, key, new_things_json, dev)

                new_ids.append(new_id) # Add to list

            
            new_things[key] = new_ids # create new item in dictionary e.g. 'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021']
        
        # if it's not an array e.g. 'trim': '098732490873x298374210398701'
        else:

            # add this object id to the list of processed ids
            processed_ids.append(value)

            # Get the json for that object id
            my_thing = common_functions.get_req(key, value, dev) # Will only work if all things are named the same as they're referenced
            # print(f"get_new_things_{iteration}: {json.dumps(my_thing)[:1000]}")
            # print('')
            
            my_thing = clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
            # print(f"get_new_things_{iteration} - clean_json: {my_thing}")
            # print('')

            things_json = find_ids(my_thing) # check to see if there are any ids attached to this thing
            # print(f"get_new_things_{iteration} - find_ids: {things_json}")
            # print('')
            
            # if there are things attached to this thing
            if things_json:
                print(f"moving onto get_new_things_{iteration+1}")
                new_things_json = get_new_things(things_json, created_by_user_id, processed_ids, iteration, dev) # returns a json with the new ids formatted the same as above but with each object copied and a new id assigned.
                for new_key in new_things_json:
                    my_thing[new_key] = new_things_json[new_key]
            else:
                print('No more things to create here')
                print('') 

            response = common_functions.post_req(key, my_thing, dev) # Create new object with the same json in the one we just got
            # print(f"get_new_things_{iteration} - post_req: {response}")
            print('')
            print('')

            new_id = response['id'] # Get the new id

            if things_json:
                update_new_things(new_id, key, new_things_json, dev)

            new_things[key] = new_id # create new item in dictionary e.g. 'trim': '098732490873x298374210398701'

    return new_things

def assign_to_proposed_scenario(new_things_json, dev, scenario_id):
    print(f"assign_to_proposed_scenario:")
    print(f"assign_to_proposed_scenario: {new_things_json}")
    scenario_proposed_response = common_functions.post_req("scenario_proposed", new_things_json, dev)
    scenario_proposed_id = scenario_proposed_response['id']

    common_functions.patch_req("scenario", scenario_id, body={"scenario_proposed": scenario_proposed_id}, dev=dev)

def assign_to_baseline_scenario(new_things_json, dev, scenario_id):

    scenario_baseline_response = common_functions.post_req("scenario_baseline", new_things_json, dev)
    scenario_baseline_id = scenario_baseline_response['id']

    common_functions.patch_req("scenario", scenario_id, body={"scenario_baseline": scenario_baseline_id}, dev=dev)


def start():
    dev, report_id, scenario_id, created_by_user_id = get_payload()

    processed_ids = []
    processed_ids.append(report_id)

    report_json = common_functions.get_req("report", report_id, dev)

    report_json = clean_json(report_json, processed_ids)

    things_json = find_ids(report_json)

    iteration = 0

    if things_json:
        new_things_proposed_json = get_new_things(things_json, created_by_user_id, processed_ids, iteration, dev)

        assign_to_proposed_scenario(new_things_proposed_json, dev, scenario_id)

        new_things_baseline_json = get_new_things(things_json, created_by_user_id, processed_ids, iteration, dev)

        assign_to_baseline_scenario(new_things_baseline_json, dev, scenario_id)






start()