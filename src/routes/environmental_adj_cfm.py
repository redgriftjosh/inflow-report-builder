import sys
import json
import common_functions

data = json.loads(sys.argv[1])
leak_entry_id = data.get('leak_entry')
dev = data.get('dev')
if dev == 'yes':
    dev = '/version-test'
else:
    dev = ''

change_all_leaks = data.get('change_all_leaks')
if change_all_leaks == "no":
    uf = data.get('uf')
    cfm = data.get('cfm')
    environmental_adjustment = data.get('environmental_adjustment')

    environmental_adj_cfm = cfm * (uf / 100) * (environmental_adjustment / 100)

    common_functions.patch_req("leak_entry", leak_entry_id, body={"environmental_adj_cfm": environmental_adj_cfm}, dev=dev)
elif change_all_leaks == "yes":
    leak_id = data.get('leak')

    leak_json = common_functions.get_req("leak", leak_id, dev)

    environmental_adjustment = leak_json["response"]["environmental_adjustment"]
    leak_entry_ids = leak_json["response"]["leak_entry"]

    for id in leak_entry_ids:
        leak_entry_json = common_functions.get_req("leak_entry", id, dev)
        uf = leak_entry_json["response"]["uf"]
        cfm = leak_entry_json["response"]["cfm"]

        environmental_adj_cfm = cfm * (uf / 100) * (environmental_adjustment / 100)
        common_functions.patch_req("leak_entry", id, body={"environmental_adj_cfm": environmental_adj_cfm}, dev=dev)


        



