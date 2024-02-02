import sys
import json
from datetime import datetime, timedelta
import os
import proposed_leaks
import proposed_7_1
import proposed_7_2

current = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(current)
sys.path.append(parent)
import common_functions

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
        scenario_id = data["scenario_id"]
    except:
        print(f"Can't find variable: scenario_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, scenario_id

def start():
    dev, report_id, scenario_id = get_payload()

    # variables = proposed_leaks.start(dev, report_id, scenario_id)

    proposed_7_1.start(dev, report_id, scenario_id)

    # proposed_7_2.start(dev, report_id, scenario_id, variables)


start()