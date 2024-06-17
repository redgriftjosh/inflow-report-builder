import sys
import json
from routes import common_functions

def get_payload():
    data = json.loads(sys.argv[1])
    report_id = data.get('report_id')
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    
    return dev, report_id

def get_dependancies(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    leak_id = report_json["response"]["leak"]

    leak_json = common_functions.get_req("leak", leak_id, dev)
    env_adj = leak_json["response"]["environmental_adjustment"]

    leak_entry_ids = leak_json["response"]["leak_entry"]

    cfms = []
    ufs = []

    for entry in leak_entry_ids:
        leak_entry_json = common_functions.get_req("leak_entry", entry, dev)
        cfms.append(leak_entry_json["response"]["uf"])
        ufs.append(leak_entry_json["response"]["cfm"])

    return env_adj, cfms, ufs, leak_id

def calculate_adj_cfm(cfms, ufs, env_adj):
    adjusted_cfms = [cfm * uf / 100 * env_adj / 100 for cfm, uf in zip(cfms, ufs)]
    return sum(adjusted_cfms)
    

def start():
    dev, report_id = get_payload()

    env_adj, cfms, ufs, leak_id = get_dependancies(report_id, dev)

    adj_cfm = calculate_adj_cfm(cfms, ufs, env_adj)

    common_functions.patch_req("leak", leak_id, body={"total_cfm_adjusted": adj_cfm}, dev=dev)



start()

# change_all_leaks = data.get('change_all_leaks')
# if change_all_leaks == "no":
#     uf = data.get('uf')
#     cfm = data.get('cfm')
#     environmental_adjustment = data.get('environmental_adjustment')

#     environmental_adj_cfm = cfm * (uf / 100) * (environmental_adjustment / 100)

#     common_functions.patch_req("leak_entry", leak_entry_id, body={"environmental_adj_cfm": environmental_adj_cfm}, dev=dev)
# elif change_all_leaks == "yes":
#     leak_id = data.get('leak')

#     leak_json = common_functions.get_req("leak", leak_id, dev)

#     environmental_adjustment = leak_json["response"]["environmental_adjustment"]
#     leak_entry_ids = leak_json["response"]["leak_entry"]

#     for id in leak_entry_ids:
#         leak_entry_json = common_functions.get_req("leak_entry", id, dev)
#         uf = leak_entry_json["response"]["uf"]
#         cfm = leak_entry_json["response"]["cfm"]

#         environmental_adj_cfm = cfm * (uf / 100) * (environmental_adjustment / 100)
#         common_functions.patch_req("leak_entry", id, body={"environmental_adj_cfm": environmental_adj_cfm}, dev=dev)


        



