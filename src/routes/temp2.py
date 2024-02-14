import numpy as np

def calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm):
    x = [(capacity_scfm*0.1), capacity_scfm]
    y = [(full_load_kw*0.55), full_load_kw]

    slope, intercept = np.polyfit(x, y, 1)

    # return slope * acfm + intercept

    print( slope * acfm + intercept)


acfm = 0
full_load_kw = 6
capacity_scfm = 1000

calculate_dryer_kw_row(acfm, full_load_kw, capacity_scfm)