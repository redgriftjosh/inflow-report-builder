import sys
import json
import subprocess
# from routes.eco_calculation import proposed_compressors, proposed_refresh_compressor_rows_7_2
# from routes.eco_calculation.proposed_refresh_compressor_rows_7_2 import start as proposed_refresh_compressor_rows_7_2
# from routes.eco_calculation.proposed_compressors import start as proposed_compressors
# from routes.eco_calculations.proposed import start as proposed


data = json.loads(sys.argv[1])
serialized_data = json.dumps(data)
scope = data["scope"]
print("Hello from eco_calculations.py")

if scope == "proposed":
    print("proposed")
    from routes.eco_calculation.proposed import start as proposed
    proposed()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed.py', serialized_data])
    # proposed.start()
elif scope == "proposed_refresh_compressor_rows_7_2":
    from routes.eco_calculation.proposed_refresh_compressor_rows_7_2 import start as proposed_refresh_compressor_rows_7_2
    proposed_refresh_compressor_rows_7_2()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_refresh_compressor_rows_7_2.py', serialized_data])
elif scope == "proposed_leaks":
    from routes.eco_calculation.proposed_leaks import start as proposed_leaks
    proposed_leaks()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_leaks.py', serialized_data])
elif scope == "proposed_drains":
    from routes.eco_calculation.proposed_drains import start as proposed_drains
    proposed_drains()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_drains.py', serialized_data])
elif scope == "proposed_dryers":
    from routes.eco_calculation.proposed_dryers import start as proposed_dryers
    proposed_dryers()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_dryers.py', serialized_data])
elif scope == "proposed_compressors":
    from routes.eco_calculation.proposed_compressors import start as proposed_compressors
    proposed_compressors()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_compressors.py', serialized_data])
elif scope == "proposed_filters":
    from routes.eco_calculation.proposed_filters import start as proposed_filters
    proposed_filters()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_filters.py', serialized_data])
elif scope == "proposed_pressure":
    from routes.eco_calculation.proposed_pressure import start as proposed_pressure
    proposed_pressure()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_pressure.py', serialized_data])
elif scope == "proposed_update_op_stats":
    print("proposed_update_op_stats")
    from routes.eco_calculation.proposed_update_op_stats import start as proposed_update_op_stats
    proposed_update_op_stats()
    # subprocess.run(['python3', 'routes/eco_calculations/proposed_update_op_stats.py', serialized_data])

elif scope == "compare_scenarios":
    from routes.eco_calculation.compare_scenarios import start as compare_scenarios
    compare_scenarios()
    # subprocess.run(['python3', 'routes/eco_calculations/compare_scenarios.py', serialized_data])

elif scope == "baseline":
    from routes.eco_calculation.baseline import start as baseline
    baseline()
    # subprocess.run(['python3', 'routes/eco_calculations/baseline.py', serialized_data])
elif scope == "baseline_refresh_compressor_rows_7_2":
    from routes.eco_calculation.baseline_refresh_compressor_rows_7_2 import start as baseline_refresh_compressor_rows_7_2
    baseline_refresh_compressor_rows_7_2()
    # subprocess.run(['python3', 'routes/eco_calculations/baseline_refresh_compressor_rows_7_2.py', serialized_data])
elif scope == "baseline_leaks":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_leaks.py', serialized_data])
elif scope == "baseline_drains":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_drains.py', serialized_data])
elif scope == "baseline_dryers":
    from routes.eco_calculation.baseline_dryers import start as baseline_dryers
    baseline_dryers()
    # subprocess.run(['python3', 'routes/eco_calculations/baseline_dryers.py', serialized_data])
elif scope == "baseline_compressors":
    from routes.eco_calculation.baseline_compressors import start as baseline_compressors
    baseline_compressors()
    # subprocess.run(['python3', 'routes/eco_calculations/baseline_compressors.py', serialized_data])
elif scope == "baseline_filters":
    subprocess.run(['python3', 'routes/eco_calculations/baseline_filters.py', serialized_data])

elif scope == "baseline_update_op_stats":
    print("baseline_update_op_stats")
    from routes.eco_calculation.baseline_update_op_stats import start as baseline_update_op_stats
    baseline_update_op_stats()
    # subprocess.run(['python3', 'routes/eco_calculations/baseline_update_op_stats.py', serialized_data])

else:
    print("eco_calculations.py cannot find the script you're looking for...", file=sys.stderr)
    sys.exit(1)