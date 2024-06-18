import json
import sys
from eco_calculation import proposed_global

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
        op_id = data["op_id"]
    except:
        print(f"Can't find variable: scenario_id", file=sys.stderr)
        sys.exit(1)

    return dev, report_id, op_id

def start():
    dev, report_id, op_id = get_payload()

    proposed_global.update_op_stats(op_id, report_id, dev)

# if __name__ == "__main__":
#     start()