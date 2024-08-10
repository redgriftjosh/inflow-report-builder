import common_functions
import sys
from utilities import requests_util

# hist_response = requests_util.post_req('histogram_2min_peak_7_2', body=None, dev='/version-test')
# print(hist_response)
# sys.exit()

response_data = requests_util.get_list_req("operation_period", "/version-test")

for result in response_data['response']['results']:
    if 'histogram_2min_peak_7_2' not in result:
        hist_response = requests_util.post_req('histogram_2min_peak_7_2', body={'operation_period': result.get('_id')}, dev='/version-test')
        requests_util.patch_req('operation_period', result.get('_id'), body={'histogram_2min_peak_7_2': hist_response.get('id')}, dev='/version-test')
        print(f"Created Hist: {hist_response.get('id')} and added to operation period: {result.get('_id')}")

