import requests
from io import StringIO
import pandas as pd
from datetime import time, datetime, timedelta

my_dict = {}

csv_url = "https://b67746bf2162451d7611c5f5e3bde12a.cdn.bubble.io/f1696125920061x287076309111290020/%231.csv"

response = requests.get(csv_url) # Step 2: Download the CSV file
response.raise_for_status() # Check that the request was successful
    
csv_data = StringIO(response.text) # Convert CSV into text of some sort
df = pd.read_csv(csv_data, skiprows=1, parse_dates=[1], date_format='%m/%d/%y %I:%M:%S %p') # Step 3: Read the CSV data into a pandas DataFrame and format the date column

print(df.head())

operating_period = {
    'Sunday': {'start': None, 'end': None},
    'Monday': {'start': time(0, 0), 'end': time(0, 0)},
    'Tuesday': {'start': time(9, 0), 'end': time(17, 0)},
    'Wednesday': {'start': time(9, 0), 'end': time(17, 0)},
    'Thursday': {'start': time(9, 0), 'end': time(17, 0)},
    'Friday': {'start': time(9, 0), 'end': time(17, 0)},
    'Saturday': {'start': None, 'end': None}
}

PRINT_DICTIONARY = {
    'Sunday': {'start': None, 'end': None}, 
    'Monday': {'start': datetime.time(9, 0), 'end': datetime.time(17, 0)}, 
    'Tuesday': {'start': datetime.time(9, 0), 'end': datetime.time(17, 0)}, 
    'Wednesday': {'start': datetime.time(9, 0), 'end': datetime.time(17, 0)}, 
    'Thursday': {'start': datetime.time(9, 0), 'end': datetime.time(17, 0)}, 
    'Friday': {'start': datetime.time(9, 0), 'end': datetime.time(17, 0)}, 
    'Saturday': {'start': None, 'end': None}
    }

Full_Dictionary = {
    '1696357876378x758860842273341400': {'1696269108682x248255198010540030': 91.52171354166667, '1696269159600x900548814629765100': 90.4870065215067},
    '1696361632915x527793690159087600': {'1696269108682x248255198010540030': 92.21504444444443, '1696269159600x900548814629765100': 91.33534074074073}
    }

filtered_dfs = []

for day, times in operating_period.items():
    start_time = times['start']
    end_time = times['end']
    
    if start_time and end_time:  # Check if both start and end times are available
        if start_time < end_time:
            mask = (
                (df.iloc[:, 1].dt.day_name() == day) &
                (df.iloc[:, 1].dt.time >= start_time) &
                (df.iloc[:, 1].dt.time <= end_time)
            )
            filtered_dfs.append(df[mask])
        elif start_time == end_time:
            mask = (
                (df.iloc[:, 1].dt.day_name() == day)
            )
            filtered_dfs.append(df[mask])
            

final_df = pd.concat(filtered_dfs)
final_df = final_df.sort_values(by=df.columns[1]).reset_index(drop=True)
final_df.to_csv(f"final_df.csv", sep=',', header=True, encoding='utf-8', index=False)

