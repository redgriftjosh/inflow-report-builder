import common_functions
import math

dev = "/version-test"
report_id = "1709055608768x171027315936985100"
ac_id = "1709057325709x609322153994616800"
ac_json = common_functions.get_req("air_compressor", ac_id, dev)
cfm = 500.8
volts = 480
rated_psig = 115
setpoint_psig = 107
pf = 0.97
pressure = 107
acfm = 237


a, b, c = common_functions.get_inverse_polynomial_vars(report_id, ac_json, cfm, volts, rated_psig, setpoint_psig, pf, pressure, dev)

amps = (a * (acfm * acfm) + b * acfm + c)
idle_kw = (amps * math.sqrt(3) * pf * volts) / 1000

print(f"a: {a}")
print(f"b: {b}")
print(f"c: {c}")

print(f"amps: {amps}")
print(f"idle_kw: {idle_kw}")



