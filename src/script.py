from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import subprocess
import os
import json
import pymysql
pymysql.install_as_MySQLdb()

app = Flask(__name__)
app.config.from_object('config')
db = SQLAlchemy(app)

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
    ip = request.headers.get("X-Real-Ip", "")
    now = datetime.utcnow().isoformat()
    job_id = f"{ip}{now}"

    data_request = request.get_json()
    report_id = data_request.get("report-id")
    dev = data_request.get("dev")

    job = Job(slug=job_id, report_id=report_id, dev=dev)
    db.session.add(job)
    db.session.commit()


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

class Job(db.Model):
    __tablename__ = "jobs"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), nullable=False)
    report_id = db.Column(db.String(255), nullable=True)
    dev = db.Column(db.String(10), nullable=True)
    state = db.Column(db.String(10), nullable=False, default="queued")
    result = db.Column(db.Integer, default=0)

# ONLY FOR TESTING LOCALLY COMMENT OUT WHEN YOU COMMIT
# if __name__ == '__main__':
#     app.run(debug=True, port=3000)