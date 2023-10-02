from flask import Flask, request, jsonify #pythons version of 'Express' it allows you to run localhost and receive webhooks
import pandas as pd #For calcuations on dataframes.
import requests #to download csv from a link
from io import StringIO #We are using the StringIO class from the io module to read the CSV data from a string
from math import sqrt
from datetime import datetime, timedelta
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

@app.route('/update-report', methods=['POST'])
def update_report():
    data = request.get_json()
    serialized_data = json.dumps(data)

    script_path = os.path.join('routes', 'update-report.py')

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


@app.route('/update-3-2', methods=['POST'])
def update_update_3_2():
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


@app.route('/add-ac-data-logger', methods=['POST'])
def addAcDataLogger():
    data = request.get_json()
    csv_urls = data.get('files') # Step 1: Get the CSV file URL from the POST request dat
    
    dataframes = []

    if csv_urls:
        for csv_url in csv_urls:
            response = requests.get(csv_url) # Step 2: Download the CSV file
            response.raise_for_status() # Check that the request was successful
            
            csv_data = StringIO(response.text) # Convert CSV into text of some sort
            df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column

            dataframes.append(df)
        
        master_df = pd.concat(dataframes)

        #print(df.dtypes)

        def calculate_kilowatts(amps):
            return min(round(amps * 400 * (0.6 if amps < 100 else 0.8) * sqrt(3) / 1000, 2), 110 * 0.746)
        
        master_df['Kilowatts'] = master_df.iloc[:, 2].apply(calculate_kilowatts)
        
        master_df.info()
        
        max_amps = master_df.iloc[:, 2].max()
        master_df['ACFM'] = master_df.iloc[:, 2].apply(lambda x: calculate_acfm(x, max_amps))

        start_times = [datetime.strptime(time, '%I:%M %p').time() for time in data['start_times']]
        end_times = [datetime.strptime(time, '%I:%M %p').time() for time in data['end_times']]
        operating_periods = data['operating_period_names']
        operating_period_ids = data['operating_period_ids']

        for start_time, end_time, period_name, period_id in zip(start_times, end_times, operating_periods, operating_period_ids):
            if start_time < end_time:
                period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) & (master_df.iloc[:, 1].dt.time < end_time)]
            else:  # Case for overnight period
                period_data = master_df[(master_df.iloc[:, 1].dt.time >= start_time) | (master_df.iloc[:, 1].dt.time < end_time)]
            
            avg_acfm = period_data['ACFM'].mean()
            hours_diff = hours_between(start_time, end_time)
            avg_kilowatts = period_data['Kilowatts'].mean()
            print(f"Average Kilowatts during {period_name}: {avg_kilowatts}")
            update_operating_periods_in_bubble(period_id, avg_kilowatts, hours_diff, avg_acfm)

        # avg_amps = df.iloc[:, 2].mean()
        # print(f"Average Amps: {avg_amps}")

    return jsonify(message="Success"), 200

def update_operating_periods_in_bubble(operating_period_ids, avg_kilowatts, hours_between, avg_acfm):
    url = f"https://inflow-co.bubbleapps.io/version-test/api/1.1/obj/Operation-Period/{operating_period_ids}"
    body = {
        "kW": avg_kilowatts,
        "Hours/yr": hours_between,
        "ACFM Made": avg_acfm
    }

    print(body)

    headers = {
        "Authorization": "Bearer 6f8e90aff459852efde1bc77c672f6f1",
        "Content-Type": "application/json"
    }

    response = requests.patch(url, json=body, headers=headers)
    print(response.text)

def hours_between(start_time, end_time):
    today = datetime.today()
    start_datetime = datetime.combine(today, start_time)
    end_datetime = datetime.combine(today, end_time)

    if end_datetime <= start_datetime:
        end_datetime += timedelta(days=1)
    
    time_difference = end_datetime - start_datetime
    hours_difference = time_difference.total_seconds() / 3600 * 365

    return hours_difference

def calculate_acfm(amps, max_amps):
    return 0 if amps < (max_amps - 14) else 434

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
