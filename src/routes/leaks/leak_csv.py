from routes import common_functions
import json
import sys

def delete_existing_leaks(leak_json, report_id, dev):
    try:
        leak_entries = leak_json["response"]["leak_entry"]
        for i, entry in enumerate(leak_entries):
            common_functions.patch_req("Report", report_id, body={"loading": f"deleting existing leaks: {i+1}", "is_loading_error": "no"}, dev=dev)
            common_functions.del_req("leak_entry", entry, dev)
    except:
        print(f"No existing leaks to delete  guess..")

def get_payload():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    print(f"Data: {data}")

    # data = json.loads(local_data)
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    # next 2 lines are for running the code without the webhook. REPORT ID: 1696116368926x296884495425208300
    # local_data = '{"report-id": "1696116368926x296884495425208300"}'

    report_id = data.get('report_id')

    report_json = common_functions.get_req("Report", report_id, dev)

    leak_id = report_json["response"]["leak"]
    leak_json = common_functions.get_req("leak", leak_id, dev)

    delete_existing_leaks(leak_json, report_id, dev)


    if "csv" in leak_json["response"]:
        csv_url = leak_json["response"]["csv"]
        csv_url = f"https:{csv_url}"
    else:
        print(f"Cannot Find Leak CSV", file=sys.stderr)
        sys.exit(1)

    try:
        row_first = leak_json["response"]["row_first"]
        if row_first is None:
            print("row_first is missing", file=sys.stderr)
            sys.exit(1)
    except:
        print("row_first is missing", file=sys.stderr)
        sys.exit(1)
    try:
        row_first = int(row_first) - 1
        print(f"Row First: {row_first}")
    except ValueError:
        print("row_first is not a valid integer", file=sys.stderr)
        sys.exit(1)
    
    columns = get_columns(["column_area", "column_category", "column_cfm", "column_date", "column_eq", "column_fixed", "column_id", "column_location", "column_note", "column_tagged", "column_uf"], leak_id, dev)

    return csv_url, leak_id, dev, report_id, row_first, columns

def process_csv(csv_url, row_first, columns, leak_id):
    import requests
    import csv
    from io import StringIO

    response = requests.get(csv_url)
    csv_data = response.text
    # csv_reader = csv.DictReader(StringIO(csv_data))
    for _ in range(row_first):
        next(StringIO(csv_data))
    csv_reader = csv.reader(StringIO(csv_data))
    print (f"CSV Reader: {csv_data}")

    entries = []
    for i, row in enumerate(csv_reader):
        if i >= row_first:
            # row_values = list(row.values())
            print(f"Row: {row}")
            entry = {}
            for key, index in columns.items():
                if index is not None:
                    if key in ["tagged", "euipment_shutdown_required", "fixed"]:
                        print (f"Index [3, 4, 8]: {index}")
                        entry[key] = row[index].strip().lower() == 'y'
                        print (f"entry[key] = row[index].strip().lower() == 'y': {row[index].strip().lower() == 'y'}")
                    else:
                        entry[key] = row[index]
            entry["collapsed"] = True
            entry["leak"] = leak_id
            entries.append(entry)

    print (f"Entries: {entries}")
    return entries

def get_columns(column_names, leak_id, dev):
    column_output_names = ["area", "category", "cfm", "date_leak_found", "euipment_shutdown_required", "fixed", "asset_id", "location", "note", "tagged", "uf"]
    columns = {}
    leak_json = common_functions.get_req("leak", leak_id, dev)
    for i, column_name in enumerate(column_names):
        try:
            column_value = leak_json["response"][column_name]
            if column_value:
                columns[column_output_names[i]] = column_letter_to_index(column_value)
            else:
                columns[column_output_names[i]] = None
        except:
            columns[column_output_names[i]] = None
    print (f"Columns: {columns}")
    return columns

def column_letter_to_index(column_letter):
    column_letter = column_letter.strip().upper()
    index = 0
    for char in column_letter:
        index = index * 26 + (ord(char) - ord('A'))
    return index

def start():
    csv_url, leak_id, dev, report_id, row_first, columns = get_payload()

    entries = process_csv(csv_url, row_first, columns, leak_id)

    new_leak_ids = []
    for i, entry in enumerate(entries):
        try:
            common_functions.patch_req("Report", report_id, body={"loading": f"Creating New Leaks: {i+1}", "is_loading_error": "no"}, dev=dev)
            response = common_functions.post_req("leak_entry", body=entry, dev=dev)
            new_leak_ids.append(response.get('id'))
        except:
            print(f"Error creating leak for row: {i+1}. Check to make sure number columns only contain numbers.", file=sys.stderr)
            common_functions.patch_req("leak", leak_id, body={"leak_entry": new_leak_ids}, dev=dev)
            sys.exit(1)
        

    common_functions.patch_req("leak", leak_id, body={"leak_entry": new_leak_ids}, dev=dev)
    leak = {
        "leak": leak_id,
        "area": "Hello"
    }
    print(f"Response: {response.get('id')}")




start()
    