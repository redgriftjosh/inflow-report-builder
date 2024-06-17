import sys
from utilities import requests_util
import numpy as np


def timed_kw_calc(dryer_json, full_load_kw):
    try:
        # e.g. 50
        load_factor = dryer_json["response"]["desiccant_load_factor_kw"]
    except:
        print(f"Missing Load Factor for Timed Dryer", file=sys.stderr)
        sys.exit(1)
    
    avg_kw = full_load_kw * (load_factor / 100)

    return avg_kw

def dpd_kw_calc(acfm, full_load_kw, capacity_scfm, dryer_json):
    try:
        multiplication_factor = dryer_json["response"]["multiplication_factor_cfm"]
    except:
        multiplication_factor = 1
        
    acfm = acfm * multiplication_factor

    try:
        # e.g. 50
        load_factor = dryer_json["response"]["desiccant_load_factor_kw"]
    except:
        print(f"Missing Load Factor for Dew Point Demand Dryer", file=sys.stderr)
        sys.exit(1)
    
    operational_factor = acfm / capacity_scfm

    avg_kw = full_load_kw * (load_factor / 100) * operational_factor

    return avg_kw

def get_ac_ids_for_dryer(report_json, connected_to, dev):
    ac_ids = report_json["response"]["air_compressor"]

    connected_to_list = connected_to.split(", ")

    connected_ac_ids = []

    idxs = []
    for idx, ac_id in enumerate(ac_ids):
        ac_json = requests_util.get_req("air_compressor", ac_id, dev)
        name = ac_json["response"]["Customer CA"]
        
        if name in connected_to_list:
            connected_ac_ids.append(ac_id)
            idxs.append(idx+1)
        
    
    return connected_ac_ids, idxs

def calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm, dryer_json):
    try:
        multiplication_factor = dryer_json["response"]["multiplication_factor_cfm"]
    except:
        multiplication_factor = 1

    acfm = acfm * multiplication_factor

    x = [(capacity_scfm*0.1), capacity_scfm]
    y = [(full_load_kw*0.55), full_load_kw]

    slope, intercept = np.polyfit(x, y, 1)

    return slope * acfm + intercept

def get_cfm_loss_dpd(acfm, capacity_scfm, type):
    operational_factor = acfm / capacity_scfm

    if type == "Desiccant Dryer No Heat":
        cfm_loss = capacity_scfm * 0.18 * operational_factor
        return cfm_loss
    elif type == "Desiccant With Heat":
        cfm_loss = capacity_scfm * 0.08 * operational_factor
        return cfm_loss
    elif type == "Desiccant With Heat & Blower":
        cfm_loss = capacity_scfm * 0.03 * operational_factor
        return cfm_loss
    elif type == "Refrigerated":
        cfm_loss = 0
        return cfm_loss

def get_dryer_cfm_loss(capacity_scfm, type):
    
    if type == "Desiccant Dryer No Heat":
        cfm_loss = capacity_scfm * 0.18
        return cfm_loss
    elif type == "Desiccant With Heat":
        cfm_loss = capacity_scfm * 0.08
        return cfm_loss
    elif type == "Desiccant With Heat & Blower":
        cfm_loss = capacity_scfm * 0.03
        return cfm_loss
    elif type == "Refrigerated":
        cfm_loss = 0
        return cfm_loss