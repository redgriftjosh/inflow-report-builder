from flask import Flask, request, jsonify #pythons version of 'Express' it allows you to run localhost and receive webhooks
import subprocess
import os
import json
from threading import Thread

app = Flask(__name__)

@app.route('/graph-to-pressure-sensor', methods=['POST'])
def graph_to_pressure_sensor():
    data = request.get_json()

    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'graph-to-pressure-sensor.py')
    completed_process = subprocess.run(['python3', script_path, serialized_data])

    if completed_process.returncode == 0:
        return jsonify(message="We did it!"), 200
    else:
        return jsonify(message="Sorry bout that one, boss..."), 500



@app.route('/graph-to-ac', methods=['POST'])
def graph_to_ac():
    data = request.get_json()
    # print(f"Received data for /graph-to-ac: {data}")

    serialized_data = json.dumps(data)
    
    script_path = os.path.join('routes', 'graph-to-ac.py')
    completed_process = subprocess.run(['python3', script_path, serialized_data])

    if completed_process.returncode == 0:
        return jsonify(message="Success!"), 200
    else:
        return jsonify(message="Looks like we might have potentially encountered a teeny weeny error..."), 500

@app.route('/update-3-2', methods=['POST'])
def update_3_2():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-2.py')

    def run_script():
        subprocess.run(['python3', script_path, serialized_data])
        
    # completed_process = subprocess.run(['python3', script_path, serialized_data])

    # Using Threat to provide a success message before running the script because it can take ~30 seconds to run the script and the user is locked down until success message
    Thread(target=run_script).start()

    return jsonify(message="Success!"), 200
    
    # if completed_process.returncode == 0:
    #     return jsonify(message="Success!"), 200
    # else:
    #     return jsonify(message="Oh Jeez..."), 500
    
@app.route('/update-3-1', methods=['POST'])
def update_3_1():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-1.py')

    def run_script():
        subprocess.run(['python3', script_path, serialized_data])
        
    # completed_process = subprocess.run(['python3', script_path, serialized_data])

    # Using Threat to provide a success message before running the script because it can take ~30 seconds to run the script and the user is locked down until success message
    Thread(target=run_script).start()

    return jsonify(message="Success!"), 200
    
    # if completed_process.returncode == 0:
    #     return jsonify(message="Success!"), 200
    # else:
    #     return jsonify(message="Oh Jeez..."), 500

@app.route('/update-3-3', methods=['POST'])
def update_3_3():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-3.py')

    def run_script():
        subprocess.run(['python3', script_path, serialized_data])
        
    # completed_process = subprocess.run(['python3', script_path, serialized_data])

    # Using Threat to provide a success message before running the script because it can take ~30 seconds to run the script and the user is locked down until success message
    Thread(target=run_script).start()

    return jsonify(message="Success!"), 200
    
    # if completed_process.returncode == 0:
    #     return jsonify(message="Success!"), 200
    # else:
    #     return jsonify(message="Oh Jeez..."), 500