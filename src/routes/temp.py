pressure = 108.05503277453907
pressure_change = 0.0

pressure_correct = pressure + pressure_change

psi_percent = 1-((pressure-pressure_correct)*0.005)

print(f"psi_percent: {psi_percent}")