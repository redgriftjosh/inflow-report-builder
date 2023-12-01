import sys
import json
import common_functions

data = json.loads(sys.argv[1])
leak_entry_id = data.get('leak_entry')
uf = data.get('uf')
cfm = data.get('cfm')
dev = data.get('dev')
if dev == 'yes':
    dev = '/version-test'
else:
    dev = ''

adjusted_cfm = cfm * (uf / 100)

common_functions.patch_req("leak_entry", leak_entry_id, body={"adjusted_cfm": adjusted_cfm}, dev=dev)

