import common_functions
import sys
import json
import re

def clean_json(my_json, processed_ids):
    my_json = my_json['response']
    keys_to_remove = ["_id", "Modified Date", "Created Date", "Created By", "created_by_user_id"]

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

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this

    # next 2 lines are for running the code without the webhook. REPORT ID: 1696116368926x296884495425208300
    # local_data = '{"report-id": "1696116368926x296884495425208300", "clone_name": "Report Copy", "dev": "yes"}'
    # data = json.loads(local_data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    try:
        report_name = data.get('clone_name')
    except:
        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"No Name for your report.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    processed_ids = []
    report_id = data.get('report-id')

    processed_ids.append(report_id)

    iteration = 0

    report_json = common_functions.get_req("report", report_id, dev)
    created_by_user_id = report_json["response"]["created_by_user_id"]

    # print(f"1 - Dirty Report Json: {report_json}")
    print('')
    try:
        report_json = clean_json(report_json, processed_ids)
        # print(f"1 - Cleaned Report Json: {report_json}")
        print('')
    except:
        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"trouble cleaning report_json (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    try:
        things_json = find_ids(report_json) # returns the report_json but only with thing ids e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
        # print(f"1 - ONLY IDS: {things_json}")
        print('')
    except:
        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"trouble with find_ids (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if things_json:
        new_things_json = get_new_things(things_json, created_by_user_id, processed_ids, iteration, dev) # returns a json with the new ids formatted the same as above but with each object copied and a new id assigned.
        # print(f"1 - NEW ONLY IDS: {things_json}")
        # print('')

        for key in new_things_json:
            report_json[key] = new_things_json[key]

    report_json['Report Name'] = report_name
    report_json['created_by_user_id'] = created_by_user_id

    # print(f"1 - Final Report JSON: {report_json}")
    # print('')
    response = common_functions.post_req("report", report_json, dev)
    new_report_id = response['id']
    new_type = 'report'

    if things_json:
        update_new_things(new_report_id, new_type, new_things_json, dev)
    
    common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"Success!", "is_loading_error": "no"}, dev=dev)

start()


# test()