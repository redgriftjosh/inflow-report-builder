import common_functions

# report_id = "1697665600466x124847461118842600"

dev = "/version-test"

# report_json = common_functions.get_req("report", report_id, dev)

# op_ids = report_json["response"]["operation_period"]
# print(op_ids)

report_id = "1700272567193x756672560062005200"

report_json = common_functions.get_req("report", report_id, dev)

def get_total_annual_operating_hours(report_json, dev):
    if report_json["response"]["operating_period_type"] != "Experimental":
        op_ids = report_json["response"]["operation_period"]
        hrs_yr = []
        for id in op_ids:
            op_json = common_functions.get_req("operation_period", id, dev)
            hrs = op_json["response"]["Hours/yr"]
            hrs_yr.append(hrs)
        
        total_hrs = sum(hrs_yr)

        return total_hrs
    else:
        op_ids = report_json["response"]["operation_period"]
        base_weekly_schedule = [False] * 10080
        for id in op_ids:
            _, weekly_schedule = common_functions.minutes_between_experimental(id, dev)
            for i in range(10080):
                if base_weekly_schedule[i] == False:   
                    base_weekly_schedule[i] = weekly_schedule[i]
        
        total_hrs = sum(base_weekly_schedule) / 60
        return total_hrs

print(get_total_annual_operating_hours(report_json, dev) * 52)