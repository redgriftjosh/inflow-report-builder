import common_functions
import sys
import json
from utilities import compressor_util, requests_util


def get_payload():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''

    report_id = data['report_id']

    return dev, report_id

# def get_max_cfm_from_slopes(ac_json, ac_name, dev):
#     try:
#         slope_ids = ac_json["response"]["vfd_slope_entries"]
#     except:
#         print(f"Missing Slope Entries!: {ac_name}", file=sys.stderr)
#         sys.exit(1)
    
#     slope_cfms = []
#     for slope in slope_ids:
#         slope_json = requests_util.get_req("vfd_slope_entries", slope, dev)
#         try:
#             slope_cfms.append(slope_json["response"]["capacity-acfm"])
#         except:
#             print(f"Missing Slope Data: {ac_name}", file=sys.stderr)
#             sys.exit(1)
    
#     return max(slope_cfms)


def get_cfms(report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    try:
        ac_ids = report_json["response"]["air_compressor"]
    except:
        print(f"Missing Air Compressors!", file=sys.stderr)
        sys.exit(1)

    cfms = []
    for idx, ac_id in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac_id, dev)

        try:
            ac_name = ac_json["response"]["Customer CA"]
        except:
            print(f"Missing Air Compressor Name!!!! AC{idx+1}? (my best guess)", file=sys.stderr)
            sys.exit(1)
        
        try:
            control = ac_json["response"]["Control Type"]
        except:
            print(f"Missing Control Type! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)
        
        cfms.append(compressor_util.get_cfm(control, ac_json, ac_name, dev))

        # if control == "Fixed Speed - Variable Capacity":
        #     cfms.append(get_max_cfm_from_slopes(ac_json, ac_name, dev))
        # else:
        #     try:
        #         cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        #         cfms.append(cfm)
        #     except:
        #         print(f"Missing CFM! Air Compressor: {ac_name}", file=sys.stderr)
        #         sys.exit(1)

    return cfms

def get_max_flows(report_id, dev):
    report_json = requests_util.get_req("report", report_id, dev)
    try:
        op_ids = report_json["response"]["operation_period"]
    except:
        print(f"Missing Operation Periods...", file=sys.stderr)
        sys.exit(1)
    
    flows = []
    for op_id in op_ids:
        op_json = requests_util.get_req("operation_period", op_id, dev)
        try:
            flow = op_json["response"]["ACFM Made"]
            flows.append(flow)
        except:
            print(f"Missing Peak Flow!", file=sys.stderr)
            sys.exit(1)
    
    return max(flows), report_json["response"]["15 Min Peak Flow"], report_json["response"]["2 Min Peak Flow"]



def start():
    dev, report_id = get_payload()
    cfms = get_cfms(report_id, dev)
    max_flow_op, max_avg_15, max_avg_2 = get_max_flows(report_id, dev)

    largest_cfm = max(cfms)
    supply_capacity = sum(cfms)
    redundancy = supply_capacity-max_flow_op-largest_cfm
    redundancy15 = supply_capacity-max_avg_15-largest_cfm
    redundancy2 = supply_capacity-max_avg_2-largest_cfm
    print(f"cfms: {cfms}")
    print(f"max_flow_op: {max_flow_op}")
    print(f"max_avg_15: {max_avg_15}")
    print(f"max_avg_2: {max_avg_2}")
    print(f"")
    print(f"largest_cfm: {largest_cfm}")
    print(f"supply_capacity: {supply_capacity}")
    print(f"")
    print(f"redundancy: {redundancy}")
    print(f"redundancy15: {redundancy15}")
    print(f"redundancy2: {redundancy2}")

    body = {
        "redundancy": redundancy,
        "redundancy-15": redundancy15,
        "redundancy-2": redundancy2,
        "supply-capacity": supply_capacity
    }

    requests_util.patch_req("Report", report_id, body, dev)
    requests_util.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)

start()

# my_dict_compile_master = common_functions.compile_master_df(report_id, dev)

# requests_util.patch_req("Report", report_id, body={"loading": f"Got all the calculations, updating chart...", "is_loading_error": "no"}, dev=dev)
# cfms = my_dict_compile_master["cfms"]
# max_flow_op = my_dict_compile_master["max_flow_op"]
# max_avg_15 = my_dict_compile_master["max_avg_15"]
# max_avg_2 = my_dict_compile_master["max_avg_2"]


# largest_cfm = max(cfms)
# supply_capacity = sum(cfms)
# redundancy = supply_capacity-max_flow_op-largest_cfm
# redundancy15 = supply_capacity-max_avg_15-largest_cfm
# redundancy2 = supply_capacity-max_avg_2-largest_cfm
# print(f"cfms: {cfms}")
# print(f"max_flow_op: {max_flow_op}")
# print(f"max_avg_15: {max_avg_15}")
# print(f"max_avg_2: {max_avg_2}")
# print(f"")
# print(f"largest_cfm: {largest_cfm}")
# print(f"supply_capacity: {supply_capacity}")
# print(f"")
# print(f"redundancy: {redundancy}")
# print(f"redundancy15: {redundancy15}")
# print(f"redundancy2: {redundancy2}")

# body = {
#     "redundancy": redundancy,
#     "redundancy-15": redundancy15,
#     "redundancy-2": redundancy2,
#     "supply-capacity": supply_capacity
# }

# requests_util.patch_req("Report", report_id, body, dev)
# requests_util.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)