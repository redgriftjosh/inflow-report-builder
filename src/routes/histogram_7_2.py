import numpy as np
import plotly.graph_objects as go
import common_functions
import sys
import plotly.io as pio
import json

def get_order_height(hist_id, ac_ids, dev):
    try:
        hist_json = common_functions.get_req("histogram_7_2", hist_id, dev)
        order_height = hist_json["response"]["order_bar_height"]
        order_height = [int(item.strip()) for item in order_height.split(',')]
        if len(order_height) == len(ac_ids):
            return order_height
        else:
            my_var = 0 / 0
    except:
        order_height = []
        for idx, ac in enumerate(ac_ids):
            order_height.append(idx+1)
        return order_height

def create_hist_2min_peak(order_height, hist_id, acfms, colours, height, dev):

    # I have no idea how this works. I assembled it through trial and error but I do not fully understand it.

    hist_values = acfms

    temp_hist_values = []
    for idx, order in enumerate(order_height):
        temp_hist_values.append(hist_values[order_height.index(min(order_height)+idx)])

    print(temp_hist_values)

    temp_order_height = []
    for idx, order in enumerate(order_height):
        temp_order_height.append(order_height.index(min(order_height)+idx))

    print(temp_order_height)

    base_values = [0, 3, 4]
    # goal base = [3, 0, 1]


    new_base = []

    for idx, hist in enumerate(hist_values):
        if idx == 0:
            new_base = [0]
        else:
            temp_base = temp_hist_values[idx-1] + new_base[idx-1] # 3
            new_base.append(temp_base)

    print(new_base)


    final_base_values = []
    for idx, order in enumerate(temp_order_height):
        final_base_values.append(new_base[temp_order_height.index(min(temp_order_height)+idx)])

    print(final_base_values)

    bins = len(hist_values) + 1
    bin_edges = []
    for i in range(bins):
        bin_edges.append(i)

    # Plotting
    # fig = go.Figure(data=[go.Bar(x=bin_edges[:-1], y=hist_values, base=new_base_values)])

    fig = go.Figure(data=[go.Bar(
        x=bin_edges[:-1],
        y=hist_values,
        base=final_base_values,
        hoverinfo='none',
        marker=dict(color=colours)
        )])


    # Set axis labels and title
    # fig.update_layout(title="Modified Histogram with Empty Space",
    #                 xaxis_title="Value",
    #                 yaxis_title="Frequency")
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, ticklen=0, zeroline=False, fixedrange=True),
        yaxis=dict(showticklabels=False, ticklen=0, zeroline=False, fixedrange=True, range=[0, height]),
        bargap=0,
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=200
    )

    # Show the figure as a static image
    # html_string = pio.to_html(fig, full_html=False, config={'displayModeBar': False})
    html_string = pio.to_html(fig, full_html=False, config={'displayModeBar': False, 'staticPlot': True})


    total_acfm = sum(hist_values)
    body = {
        "total_acfm": total_acfm,
        "histogram_html": html_string,
        "individual_acfm": hist_values
    }

    common_functions.patch_req("histogram_2min_peak_7_2", hist_id, body, dev)
    print(total_acfm)

def create_hist(order_height, hist_id, acfms, colours, height, dev):

    # I have no idea how this works. I assembled it through trial and error but I do not fully understand it.

    hist_values = acfms

    temp_hist_values = []
    for idx, order in enumerate(order_height):
        temp_hist_values.append(hist_values[order_height.index(min(order_height)+idx)])

    print(temp_hist_values)

    temp_order_height = []
    for idx, order in enumerate(order_height):
        temp_order_height.append(order_height.index(min(order_height)+idx))

    print(temp_order_height)

    base_values = [0, 3, 4]
    # goal base = [3, 0, 1]


    new_base = []

    for idx, hist in enumerate(hist_values):
        if idx == 0:
            new_base = [0]
        else:
            temp_base = temp_hist_values[idx-1] + new_base[idx-1] # 3
            new_base.append(temp_base)

    print(new_base)


    final_base_values = []
    for idx, order in enumerate(temp_order_height):
        final_base_values.append(new_base[temp_order_height.index(min(temp_order_height)+idx)])

    print(final_base_values)

    bins = len(hist_values) + 1
    bin_edges = []
    for i in range(bins):
        bin_edges.append(i)

    # Plotting
    # fig = go.Figure(data=[go.Bar(x=bin_edges[:-1], y=hist_values, base=new_base_values)])

    fig = go.Figure(data=[go.Bar(
        x=bin_edges[:-1],
        y=hist_values,
        base=final_base_values,
        hoverinfo='none',
        marker=dict(color=colours)
        )])


    # Set axis labels and title
    # fig.update_layout(title="Modified Histogram with Empty Space",
    #                 xaxis_title="Value",
    #                 yaxis_title="Frequency")
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showticklabels=False, ticklen=0, zeroline=False, fixedrange=True),
        yaxis=dict(showticklabels=False, ticklen=0, zeroline=False, fixedrange=True, range=[0, height]),
        bargap=0,
        showlegend=False,
        margin=dict(t=0, b=0, l=0, r=0),
        height=200
    )

    # Show the figure as a static image
    # html_string = pio.to_html(fig, full_html=False, config={'displayModeBar': False})
    html_string = pio.to_html(fig, full_html=False, config={'displayModeBar': False, 'staticPlot': True})


    total_acfm = sum(hist_values)
    body = {
        "total_acfm": total_acfm,
        "histogram_html": html_string,
        "individual_acfm": hist_values
    }

    common_functions.patch_req("histogram_7_2", hist_id, body, dev)
    print(total_acfm)

def acfm_2min_peak_values(dfs, op_id, report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    op_per_type = report_json["response"]["operating_period_type"]
    
    if op_per_type == "Daily":
        acfms = []
        for df in dfs:
            period_data = common_functions.daily_operating_period(df, op_id, dev) # Filter dataframe to operating period
            max_avg_2 = period_data.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
            acfms.append(max_avg_2)
        return acfms

    elif op_per_type == "Weekly":
        acfms = []
        for df in dfs:
            period_data = common_functions.weekly_operating_period(df, op_id, dev) # Filter dataframe to operating period
            max_avg_2 = period_data.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
            acfms.append(max_avg_2)
        return acfms

    elif op_per_type == "Experimental":
        acfms = []
        for df in dfs:
            period_data = common_functions.experimental_operating_period(df, op_id, dev) # Filter dataframe to operating period
            max_avg_2 = period_data.filter(like='ACFM').sum(axis=1)[::-1].rolling(window=10, min_periods=10).mean()[::-1].fillna(0).max()
            acfms.append(max_avg_2)
        return acfms

def acfm_values(dfs, op_id, report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    op_per_type = report_json["response"]["operating_period_type"]
    acfm_per_op = {}
    
    if op_per_type == "Daily":
        acfms = []
        for df in dfs:
            period_data = common_functions.daily_operating_period(df, op_id, dev) # Filter dataframe to operating period
            acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            acfms.append(acfm)
        return acfms

    elif op_per_type == "Weekly":
        acfms = []
        for df in dfs:
            period_data = common_functions.weekly_operating_period(df, op_id, dev) # Filter dataframe to operating period
            acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            acfms.append(acfm)
        return acfms
    
    elif op_per_type == "Experimental":
        acfms = []
        for df in dfs:
            period_data = common_functions.experimental_operating_period(df, op_id, dev) # Filter dataframe to operating period
            acfm = period_data.filter(like='ACFM').sum(axis=1).mean()
            acfms.append(acfm)
        return acfms

def get_df_for_each_ac(ac_ids, report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)

    my_dfs = []

    for idx, ac in enumerate(ac_ids):
        common_functions.patch_req("Report", report_id, body={"loading": f"Starting on Air Compressor {idx + 1}...", "is_loading_error": "no"}, dev=dev)
        
        
        # Get the Air Compressor into a DataFrame
        ac_json = common_functions.get_req("air_compressor", ac, dev)
        if "ac_data_logger" in ac_json["response"]:
            ac_data_logger_id = ac_json["response"]["ac_data_logger"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing data loggers! Make sure each Air Compressor has a Properly Formatted CSV uploaded. Air Compressor: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        ac_data_logger_json = common_functions.get_req("ac_data_logger", ac_data_logger_id, dev)
        
        if "Customer CA" in ac_json["response"]:
            ac_name = ac_json["response"]["Customer CA"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Name! Air Compressor ID: {ac}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()

        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Reading CSV...", "is_loading_error": "no"}, dev=dev)
        csv_url = ac_data_logger_json["response"]["CSV"]
        csv_url = f"https:{csv_url}"

        df = common_functions.csv_to_df(csv_url)

        # Trim & Exclude specified data
        if "trim" in report_json["response"] and report_json["response"]["trim"] != []:
            df = common_functions.trim_df(report_json, df, dev)
            common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Trimming CSV...", "is_loading_error": "no"}, dev=dev)

        if "exclusion" in report_json["response"]:
            df = common_functions.exclude_from_df(df, report_json, dev)
            common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Excluding from CSV...", "is_loading_error": "no"}, dev=dev)
        
        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: Kilowatts Column...", "is_loading_error": "no"}, dev=dev)
        # Create Kilowatts column
        
        if "volts" in ac_json["response"]:
            volts = ac_json["response"]["volts"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Volts! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        # df["Kilowatts"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_kilowatts(amps, volts, pf50, amppf, bhp, pf))

        common_functions.patch_req("Report", report_id, body={"loading": f"Air Compressor {idx + 1}: ACFM Column...", "is_loading_error": "no"}, dev=dev)
        # Create ACFM Column

        if "Control Type" in ac_json["response"]:
            control = ac_json["response"]["Control Type"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": f"Missing Control Type! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        
        if "CFM" in ac_json["response"]:
            cfm = ac_json["response"]["CFM"] # Used as "CFM" in OLOL calcs and "Max CFM at setpoint psig" in VFD calcs
        else:
            cfm = 1
            # common_functions.patch_req("Report", report_id, body={"loading": f"Missing CFM! Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
            # sys.exit(1)
        
        df = common_functions.calculate_flow(df, control, cfm, volts, dev, idx, ac_name, ac_json, report_id)

        # if control == "OLOL":
        #     if "threshold-value" in ac_json["response"]:
        #         threshold = ac_json["response"]["threshold-value"]
        #     else:
        #         common_functions.patch_req("Report", report_id, body={"loading": f"Missing Threshold Value! This is needed for ACFM calculations on OLOL control types. Air Compressor: {ac_name}", "is_loading_error": "yes"}, dev=dev)
        #         sys.exit()
        #     df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_olol_acfm(amps, threshold, cfm))
        # elif control == "VFD":
        #     slope, intercept = common_functions.calculate_slope_intercept(report_id, ac_json, cfm, volts, dev)
        #     df["ACFM"] = df.iloc[:, 2].apply(lambda amps: common_functions.calculate_vfd_acfm(amps, slope, intercept))
        
        my_dfs.append(df)
    return my_dfs

def get_op_id(report_id, hist_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    if "operation_period" in report_json["response"] and report_json["response"]["operation_period"] != []:
        operating_period_ids = report_json["response"]["operation_period"]
        for op_id in operating_period_ids:
            op_json = common_functions.get_req("operation_period", op_id, dev)
            if op_json["response"]["histogram_7_2"] == hist_id:
                return op_id
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Operating Periods Found! You need at least one Operating Period.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    return operating_period_ids

def get_ac_ids(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    if "air_compressor" in report_json["response"] and report_json["response"]["air_compressor"] != []:
        ac_ids = report_json["response"]["air_compressor"]
        common_functions.patch_req("Report", report_id, body={"loading": f"Found {len(ac_ids)} Air Compressor{'s' if len(ac_ids) != 1 else ''}...", "is_loading_error": "no"}, dev=dev)
    else:
        common_functions.patch_req("Report", report_id, body={"loading": "No Air Compressors Found! You need at least one Air Compressor.", "is_loading_error": "yes"}, dev=dev)
        sys.exit()
    return ac_ids

def reset_histogram_7_2(report_id, dev):
    report_json = common_functions.get_req("report", report_id, dev)
    op_ids = report_json["response"]["operation_period"]
    for op_id in op_ids:
        operation_json = common_functions.get_req("operation_period", op_id, dev)
        if "Name" in operation_json["response"]:    
            op_name =  operation_json["response"]["Name"]
        else:
            common_functions.patch_req("Report", report_id, body={"loading": "Forgot to Name your Operating Period", "is_loading_error": "yes"}, dev=dev)
            sys.exit()
        if "histogram_7_2" in operation_json["response"] and operation_json["response"]["histogram_7_2"] != []:
            hist_id = operation_json["response"]["histogram_7_2"]
            common_functions.del_req("histogram_7_2", hist_id, dev)
            print(f"Histograms have been deleted in {op_name}")
        else:
            print(f"nothing to delete in {op_name}")
        
        response = common_functions.post_req("histogram_7_2", body={"operation_period": op_id}, dev=dev)

        common_functions.patch_req("operation_period", op_id, body={"histogram_7_2": response["id"]}, dev=dev)

def get_hist_2min_peak_id(op_id, dev):
    print(f"op_id: {op_id}")
    op_json = common_functions.get_req('operation_period', op_id, dev)
    print(f"op_json: {op_json}")
    hist_2min_peak_id = op_json['response'].get('histogram_2min_peak_7_2')
    print(f"hist_2min_peak_id: {hist_2min_peak_id}")
    return hist_2min_peak_id

def get_ac_colours(ac_ids, dev):
    colours = []

    for ac_id in ac_ids:
        ac_json = common_functions.get_req('air_compressor', ac_id, dev)
        colour = ac_json['response'].get('colour')
        colours.append(colour)
    
    return colours

def get_heighest_hist(acfms, max_avg_2_acfms):
    acfms_total = sum(acfms)
    max_avg_2_acfms_total = sum(max_avg_2_acfms)

    if max_avg_2_acfms_total > acfms_total:
        return max_avg_2_acfms_total
    else:
        return acfms_total

def start():
    data = json.loads(sys.argv[1]) # Proper Code. Keep this
    dev = data.get('dev')
    if dev == 'yes':
        dev = '/version-test'
    else:
        dev = ''
    
    # get Air Compressor IDs so we can verify the right number of order height numbers.
    report_id = data.get('report_id')
    ac_ids = get_ac_ids(report_id, dev)
    colours = get_ac_colours(ac_ids, dev)

    # now we're storing the order of the bars as a list i.e. [1, 3, 4, 2]
    hist_id = data.get('hist_id')
    order_height = get_order_height(hist_id, ac_ids, dev)
    
    # reset_histogram_7_2(report_id, dev)
    op_id = get_op_id(report_id, hist_id, dev)

    hist_2min_peak_id = get_hist_2min_peak_id(op_id, dev)
    print(f"hist_2min_peak_id: {hist_2min_peak_id}")

    dfs = get_df_for_each_ac(ac_ids, report_id, dev)
    acfms = acfm_values(dfs, op_id, report_id, dev) # returns acfm per ac list = [432, 234, 234]
    print(f"acfms: {acfms}")
    max_avg_2_acfms = acfm_2min_peak_values(dfs, op_id, report_id, dev)

    hist_height = get_heighest_hist(acfms, max_avg_2_acfms)

    common_functions.patch_req("Report", report_id, body={"loading": f"Creating Your Histogram Now...", "is_loading_error": "no"}, dev=dev)
    create_hist(order_height, hist_id, acfms, colours, hist_height, dev)
    create_hist_2min_peak(order_height, hist_2min_peak_id, max_avg_2_acfms, colours, hist_height, dev)
    
    common_functions.patch_req("Report", report_id, body={"loading": f"Success!", "is_loading_error": "no"}, dev=dev)


start()