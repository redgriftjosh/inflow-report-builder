
# Really go through this if you need inspo. There are some things that don't need to be included in the baseline/proposed objects like anything that contributes to calculating flow really. Pressure and amp readings.
# Operating periods as well because they're being referenced by both baseline and proposed.
# It's all in your head if you already feel defeated. This is not a brick wall you're trying to knock over with your fists. It's a battle that you'll only win if you fight it. Don't just lay down and die.

example_report_data_structure = {
    "_id": "12345678901234567890",
    "client_name": "Anderson Windows",
    "avg_acfm": 682.92843667612, # This will be important as the baseline and proposed scenarios will be using this for many calculations
    "eco": [{ # Will define an eco object to hold all scenarios
        "scenario": { # A scenario holds all the data being used for this line on the eco table
            "end_values": { # End values are the values that are actually displayed on the row in the eco table. These are calculated based on the baseline and proposed scenarios.
                "number": 1,
                "color": "FAB515",
                "header": "Leaks",
                "sub_header": "est. 300$ per Leak Repair",
                "body": "This is my body text",
                "installed": 14000,
                "incremental": 5000,
                "dollars_per_year": 9493,
                "o_and_m": 0,
                "kw_max": 14.5,
                "kw_demand": 14.5
            },
            "baseline_scenario": { # Baseline is like a little report that uses the existing operating periods. This is default the exact same as the original report but can be modified if the user wants to compare against a different theoretical.
                "compressor": [{
                    "name": "AC1",
                    "make": "Kaeser",
                    "model": "SFR110VFD",
                    "control_type": "Variable - Fixed Speed",
                    "linked_pressure": "P1",
                    "power_factor": 0.95,
                    "volts": 440,
                    "BHP": 125
                }],
                "leaks": [{
                    "area": "P1",
                    "cfm": 3
                }],
                "operating_periods": [{
                    "name": "Days",
                    "avg_acfm": 408.8271
                    "avg_acfm_15"
                }]
            },
            "proposed_scenario": {

            }
        }
    }],
    "operating_periods": [{
        "name": "Days",
        "time_range": [{
            "days": ["Monday", "Tuesday", "Wednesday"],
            "start_time": "9:00 AM",
            "end_tiem": "5:00 PM",
            "all_day": False
        }],
        "pressure_sensors": [{
            "name": "P1",
            "avg_pressure": 91.12043204
        }],
        "avg_acfm": 408.93478172,
        "hours_per_yr": 2600
    }]
}

variable_changes = {
    "thisismyfirstopperiodid": {
        "thisisac1id": {
            "acfm": 408.08293827,
            "acfm_peak_15": 591.0438743,
            "pressure?": "May-haps-ibly"
        },
        "thisisac2id": {
            "acfm": 408.08293827,
            "acfm_peak_15": 591.0438743
        }
    },
    "thisismysecondopperiodid": {
        "thisisac1id": {
            "acfm": 398.08293827,
            "acfm_peak_15": 591.0438743
        },
        "thisisac2id": {
            "acfm": 408.08293827,
            "acfm_peak_15": 591.0438743
        }
    }
}


variables = {
    "origin": 450,
    "history": [{
        "leaks": 55
    },
    {
        "drains": 30 # Calculate this based on the report not the other scenario (basline / proposed)
    }],
    "current": 365 # = origin - sum(history.values())
}