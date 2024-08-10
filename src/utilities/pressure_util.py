import sys
from utilities import requests_util

# Returns the id of the pressure sensor and the index of the pressure sensor
def get_pressure_sensor(report_id, dev):
    report_json = requests_util.get_req("Report", report_id, dev)
    pressure_sensors = report_json["response"]["pressure_sensor"]

    idx = 0
    for sensor in pressure_sensors:
        sensor_json = requests_util.get_req("pressure_sensor", sensor, dev)
        if sensor_json["response"]["header"] == True:
            return sensor_json["response"]["_id"], idx
        
        idx += 1

def get_pressure_index(report_id, op_json, dev):
    _, i = get_pressure_sensor(report_id, dev)
    
    try:
        pressure = op_json["response"]["P2"][i]
        return pressure
    except:
        requests_util.patch_req("Report", report_id, body={"loading": "Cannot find the pressure in the Operating Period. Maybe Try running section 3.2?", "is_loading_error": "no"}, dev=dev)
        print(f"Found a Pressure Log but couldn't work with the name. Make sure it's formatted exactly like: P4", file=sys.stderr)
        sys.exit(1)