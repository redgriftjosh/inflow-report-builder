from flask import Flask, request, jsonify
import subprocess
import os
import json

app = Flask(__name__)

def run_script(data, script):
    serialized_data = json.dumps(data)
    script_path = os.path.join('routes', script)

    # This one normally pushes all console error messages as a response to the post req
    # result = subprocess.run(['python3', script_path, serialized_data], text=True, stderr=subprocess.PIPE)

    # I wanted to see the errors in the console
    result = subprocess.run(['python3', script_path, serialized_data])
    
    if result.returncode == 0:
        # If the script was successful, return the success message
        return ("Success!", 200)
    else:
        # If there was an error, return the error message
        error_message = result.stderr.strip() if result.stderr else f"Script failed with return code {result.returncode}"
        return (f"Error: {error_message}", 500)

# @app.route('/graph-to-pressure-sensor', methods=['POST'])
# def graph_to_pressure_sensor():
#     response = run_script(data = request.get_json(), script='graph-to-pressure-sensor.py')
#     return response

@app.route('/graph-to-ac', methods=['POST'])
def graph_to_ac():
    response = run_script(data = request.get_json(), script='graph-to-ac.py')
    return response

@app.route('/reset-dataset-7-2', methods=['POST'])
def reset_dataset_7_2():
    response = run_script(data = request.get_json(), script='reset_dataset_7_2.py')
    return response

@app.route('/clone_report', methods=['POST'])
def clone_report():
    response = run_script(data = request.get_json(), script='clone_report.py')
    return response

@app.route('/delete_report', methods=['POST'])
def delete_report():
    response = run_script(data = request.get_json(), script='delete_report.py')
    return response

@app.route('/data_crunch_download', methods=['POST'])
def data_crunch_download():
    response = run_script(data = request.get_json(), script='data_crunch_download.py')
    return response

@app.route('/total_output_table', methods=['POST'])
def total_output_table():
    response = run_script(data = request.get_json(), script='total_output_table.py')
    return response

@app.route('/histogram_7_2', methods=['POST'])
def histogram_7_2():
    response = run_script(data = request.get_json(), script='histogram_7_2.py')
    return response

@app.route('/update-7-2', methods=['POST'])
def update_7_2():
    response = run_script(data = request.get_json(), script='update_7_2.py')
    return response

@app.route('/update-3-2', methods=['POST'])
def update_3_2():
    response = run_script(data = request.get_json(), script='update-3-2.py')
    return response
    
@app.route('/update-3-1', methods=['POST'])
def update_3_1():
    response = run_script(data = request.get_json(), script='update-3-1.py')
    return response

@app.route('/update_3_3', methods=['POST'])
def update_3_3():
    response = run_script(data = request.get_json(), script='update_3_3.py')
    return response

@app.route('/run_backend', methods=['POST'])
def run_backend():
    data = request.get_json()
    script_name = data.get('script')
    script_body = data.get('script_body')

    response = run_script(script_body, script_name)
    return response



# ONLY FOR TESTING LOCALLY COMMENT OUT WHEN YOU COMMIT
# ./ngrok http --domain=up-marmot-tops.ngrok-free.app 3000
if __name__ == '__main__':
    app.run(debug=True, port=3000)