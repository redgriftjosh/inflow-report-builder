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

def delete_things(my_json, created_by_user_id, processed_ids, iteration, dev):
    # take the report_json with only objects e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
    iteration += 1
    # for each object attached to the report... e.g. 'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021']
    for key, value in my_json.items():
        try:
            common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"Deleting: {key}", "is_loading_error": "no"}, dev=dev)
        except:
            print(f"Could not update loading text: {key}")
        # Check if the value is an array e.g. ['12398467x219083473243224', '10843759387x0293481029374021']
        if isinstance(value, list):
            # For each id in the list...
            for id in value:

                # add this object id to the list of processed ids
                processed_ids.append(id)


                # Get the json for that object id
                my_thing = common_functions.get_req(key, id, dev) # Will only work if all things are named the same as they're referenced
                print(f"delete_things - {iteration}: {my_thing}")
                print('')
                
                my_thing = clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
                print(f"delete_things - {iteration} - clean_json: {my_thing}")
                print('')

                things_json = find_ids(my_thing) # check to see if there are any ids attached to this thing
                print(f"delete_things - {iteration} - find_ids: {things_json}")
                print('')
                
                # if there are things attached to this thing
                if things_json:
                    print(f"moving onto delete_things - {iteration+1}")
                    delete_things(things_json, created_by_user_id, processed_ids, iteration, dev)
                else:
                    print('No more things to delete here')
                    print('')
                
                response = common_functions.del_req(key, id, dev)
                print(f"delete_things - {iteration} - del_req: {response}")
                print('')
                print('')
        
        # if it's not an array e.g. 'trim': '098732490873x298374210398701'
        else:

            processed_ids.append(value)

            # Get the json for that object id
            my_thing = common_functions.get_req(key, value, dev) # Will only work if all things are named the same as they're referenced
            print(f"delete_things - {iteration}: {my_thing}")
            print('')
            
            my_thing = clean_json(my_thing, processed_ids) # get rid of the id, created by modified etc... & Processed ids
            print(f"delete_things - {iteration} - clean_json: {my_thing}")
            print('')

            things_json = find_ids(my_thing) # check to see if there are any ids attached to this thing
            print(f"delete_things - {iteration} - find_ids: {things_json}")
            print('')
            
            # if there are things attached to this thing
            if things_json:
                print(f"moving onto delete_things - {iteration+1}")
                delete_things(things_json, created_by_user_id, processed_ids, iteration, dev)
            else:
                print('No more things to delete here')
                print('')
            
            response = common_functions.del_req(key, value, dev)
            print(f"delete_things - {iteration} - del_req: {response}")
            print('')
            print('')

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

    iteration = 0

    report_json = common_functions.get_req("report", report_id, dev)
    created_by_user_id = report_json["response"]["created_by_user_id"]

    print(f"1 - Dirty Report Json: {report_json}")
    print('')
    try:
        report_json = clean_json(report_json, processed_ids)
        print(f"1 - Cleaned Report Json: {report_json}")
        print('')
    except:
        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"trouble cleaning report_json (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    try:
        things_json = find_ids(report_json) # returns the report_json but only with thing ids e.g. {'air_compressors': ['12398467x219083473243224', '10843759387x0293481029374021'], 'trim': '098732490873x298374210398701'}
        print(f"1 - ONLY IDS: {things_json}")
        print('')
    except:
        common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"trouble with find_ids (Josh's Problem)", "is_loading_error": "yes"}, dev=dev)
        sys.exit()

    if things_json:
        delete_things(things_json, created_by_user_id, processed_ids, iteration, dev) 
    

    report_json['created_by_user_id'] = created_by_user_id

    print(f"1 - deleting report: {report_json}")
    print('')
    response = common_functions.del_req("report", report_id, dev)
    print(f"del_req report: {response}")
    
    common_functions.patch_req("User", created_by_user_id, body={'loading_text': f"Success!", "is_loading_error": "no"}, dev=dev)

start()
