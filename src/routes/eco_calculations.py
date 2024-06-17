import sys
import json
import subprocess
# from routes.eco_calculations.proposed import start as proposed


data = json.loads(sys.argv[1])
serialized_data = json.dumps(data)
scope = data["scope"]
print("Hello from eco_calculations.py")

if scope == "proposed":
    print("proposed")
    subprocess.run(['python3', 'routes/eco_calculations/proposed.py', serialized_data])
    # proposed.start()
elif scope == "proposed_refresh_compressor_rows_7_2":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_refresh_compressor_rows_7_2.py', serialized_data])
elif scope == "proposed_leaks":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_leaks.py', serialized_data])
elif scope == "proposed_drains":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_drains.py', serialized_data])
elif scope == "proposed_dryers":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_dryers.py', serialized_data])
elif scope == "proposed_compressors":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_compressors.py', serialized_data])
elif scope == "proposed_filters":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_filters.py', serialized_data])
elif scope == "proposed_pressure":
    subprocess.run(['python3', 'routes/eco_calculations/proposed_pressure.py', serialized_data])
elif scope == "proposed_update_op_stats":
    print("proposed_update_op_stats")
    subprocess.run(['python3', 'routes/eco_calculations/proposed_update_op_stats.py', serialized_data])

elif scope == "compare_scenarios":
    subprocess.run(['python3', 'routes/eco_calculations/compare_scenarios.py', serialized_data])

elif scope == "baseline":
    subprocess.run(['python3', 'routes/eco_calculations/baseline.py', serialized_data])
elif scope == "baseline_refresh_compressor_rows_7_2":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_refresh_compressor_rows_7_2.py', serialized_data])
elif scope == "baseline_leaks":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_leaks.py', serialized_data])
elif scope == "baseline_drains":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_drains.py', serialized_data])
elif scope == "baseline_dryers":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_dryers.py', serialized_data])
elif scope == "baseline_compressors":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_compressors.py', serialized_data])
elif scope == "baseline_filters":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_filters.py', serialized_data])

elif scope == "baseline_update_op_stats":
    print("baseline_update_op_stats")
    subprocess.run(['python3', 'routes/eco_calculations/baseline_update_op_stats.py', serialized_data])

else:
    print("eco_calculations.py cannot find the script you're looking for...", file=sys.stderr)
    sys.exit(1)