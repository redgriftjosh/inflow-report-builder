import json
import sys
import common_functions
import time

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
        eco_table_8_1_drain_input = data["eco_table_8_1_drain_input"]
    except:
        print(f"Can't find variable: eco_table_8_1_drain_input", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, eco_table_8_1_drain_input

def add_drains_to_list(eco_table_8_1_drain_input, drain_options, dev):
    common_functions.patch_req("eco_table_8_1_drain_input", eco_table_8_1_drain_input, body={"drain_options": drain_options}, dev=dev)

def add_drain(eco_table_8_1_drain_input_json, drain_id, dev):
    # drain_selection_json = common_functions.get_req("drain_selection", drain_id, dev)
    try:
        # Check to see if we have any drains already selected
        drain_selection = eco_table_8_1_drain_input_json["response"]["drain_selection"]
    except:
        # Assuming we don't have any drains so we'll mark them all as unchecked

    

def get_drains(report_id, eco_table_8_1_drain_input, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    eco_table_8_1_drain_input_json = common_functions.get_req("eco_table_8_1_drain_input", eco_table_8_1_drain_input, dev)

    drain_ids = report_json["response"]["drain"]

    for drain_id in drain_ids:
        drain_json = common_functions.get_req("drain", drain_id, dev)
        drain_number = drain_json["response"]["drain_number"]

        add_drain(eco_table_8_1_drain_input_json, drain_id, dev)

    
        

def start():
    # Grab the variabls from the json payload
    dev, report_id, eco_table_8_1_drain_input = get_payload()

    get_drains(report_id, eco_table_8_1_drain_input, dev)


start()