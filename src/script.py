from flask import Flask, request
import subprocess
import os
import json

app = Flask(__name__)

def run_script(data, script):
    serialized_data = json.dumps(data)
    script_path = os.path.join('routes', script)
    result = subprocess.run(['python3', script_path, serialized_data])
    
    if result.returncode == 0:
        return ("Success!", 200)
    else:
        return (f"Error: {result.returncode}", 500)

@app.route('/graph-to-pressure-sensor', methods=['POST'])
def graph_to_pressure_sensor():
    response = run_script(data = request.get_json(), script='graph-to-pressure-sensor.py')
    return response

@app.route('/graph-to-ac', methods=['POST'])
def graph_to_ac():
    response = run_script(data = request.get_json(), script='graph-to-ac.py')
    return response

@app.route('/reset-dataset-7-2', methods=['POST'])
def reset_dataset_7_2():
    response = run_script(data = request.get_json(), script='reset_dataset_7_2.py')
    return response

@app.route('/data_crunch_download', methods=['POST'])
def data_crunch_download():
    response = run_script(data = request.get_json(), script='data_crunch_download.py')
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

@app.route('/update-3-3', methods=['POST'])
def update_3_3():
    response = run_script(data = request.get_json(), script='update-3-3.py')
    return response

# ONLY FOR TESTING LOCALLY COMMENT OUT WHEN YOU COMMIT
# if __name__ == '__main__':
#     app.run(debug=True, port=3000)