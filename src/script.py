from flask import Flask, request, jsonify #pythons version of 'Express' it allows you to run localhost and receive webhooks
import subprocess
import os
import json
from threading import Thread
from multiprocessing import Process

app = Flask(__name__)

def run_script(serialized_data, script_path):
    subprocess.run(['python3', script_path, serialized_data])

@app.route('/graph-to-pressure-sensor', methods=['POST'])
def graph_to_pressure_sensor():
    data = request.get_json()

    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'graph-to-pressure-sensor.py')
    p = Process(target=run_script, args=(serialized_data, script_path))
    p.start()



@app.route('/graph-to-ac', methods=['POST'])
def graph_to_ac():
    data = request.get_json()

    serialized_data = json.dumps(data)
    
    script_path = os.path.join('routes', 'graph-to-ac.py')
    p = Process(target=run_script, args=(serialized_data, script_path))
    p.start()

@app.route('/update-3-2', methods=['POST'])
def update_3_2():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-2.py')

    p = Process(target=run_script, args=(serialized_data, script_path))
    p.start()

    return jsonify(message="Success!"), 200
    
    
@app.route('/update-3-1', methods=['POST'])
def update_3_1():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-1.py')
    p = Process(target=run_script, args=(serialized_data, script_path))
    p.start()

    return jsonify(message="Success!"), 200

@app.route('/update-3-3', methods=['POST'])
def update_3_3():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-3-3.py')
    p = Process(target=run_script, args=(serialized_data, script_path))
    p.start()

    return jsonify(message="Success!"), 200


# ONLY FOR TESTING LOCALLY COMMENT OUT WHEN DEPLOYING
# if __name__ == '__main__':
#     app.run(debug=True, port=3000)