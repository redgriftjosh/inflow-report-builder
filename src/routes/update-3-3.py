import common_functions
import sys
import json
import requests

# data = json.loads(sys.argv[1]) # Proper Code. Keep this

# next 2 lines are for running the code without the webhook. REPORT ID: 1696116368926x296884495425208300
local_data = '{"report-id": "1696116368926x296884495425208300"}'
data = json.loads(local_data)

report_id = data.get('report-id')

my_dict_compile_master = common_functions.compile_master_df(report_id)

cfms = my_dict_compile_master["cfms"]
max_flow_op = my_dict_compile_master["max_flow_op"]
max_avg_15 = my_dict_compile_master["max_avg_15"]
max_avg_2 = my_dict_compile_master["max_avg_2"]


largest_cfm = max(cfms)
supply_capacity = sum(cfms)
redundancy = supply_capacity-max_flow_op-largest_cfm
redundancy15 = supply_capacity-max_avg_15-largest_cfm
redundancy2 = supply_capacity-max_avg_2-largest_cfm

body = {
    "redundancy": redundancy,
    "redundancy-15": redundancy15,
    "redundancy-2": redundancy2,
    "supply-capacity": supply_capacity
}

common_functions.patch_req("Report", report_id, body)