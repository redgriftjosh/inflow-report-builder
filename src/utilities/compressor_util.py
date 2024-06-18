import sys
from utilities import requests_util

def get_max_cfm_from_slopes(ac_json, ac_name, dev):
    try:
        slope_ids = ac_json["response"]["vfd_slope_entries"]
    except:
        print(f"Missing Slope Entries!: {ac_name}", file=sys.stderr)
        sys.exit(1)
    
    slope_cfms = []
    for slope in slope_ids:
        slope_json = requests_util.get_req("vfd_slope_entries", slope, dev)
        try:
            slope_cfms.append(slope_json["response"]["capacity-acfm"])
        except:
            print(f"Missing Slope Data: {ac_name}", file=sys.stderr)
            sys.exit(1)
    
    return max(slope_cfms)

def get_cfm(control, ac_json, ac_name, dev):
    if control == "Fixed Speed - Variable Capacity":
        return get_max_cfm_from_slopes(ac_json, ac_name, dev)
    else:
        try:
            return ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        except:
            print(f"Missing CFM! Air Compressor: {ac_name}", file=sys.stderr)
            sys.exit(1)