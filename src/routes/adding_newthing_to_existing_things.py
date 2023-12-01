import common_functions
import sys

# hist_response = common_functions.post_req('histogram_2min_peak_7_2', body=None, dev='/version-test')
# print(hist_response)
# sys.exit()

response_data = common_functions.get_list_req("operation_period", "/version-test")

for result in response_data['response']['results']:
    if 'histogram_2min_peak_7_2' not in result:
        hist_response = common_functions.post_req('histogram_2min_peak_7_2', body={'operation_period': result.get('_id')}, dev='/version-test')
        common_functions.patch_req('operation_period', result.get('_id'), body={'histogram_2min_peak_7_2': hist_response.get('id')}, dev='/version-test')
        print(f"Created Hist: {hist_response.get('id')} and added to operation period: {result.get('_id')}")

