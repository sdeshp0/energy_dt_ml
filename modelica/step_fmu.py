"""
Step an FMU one hour at a time from Python, the same way the twin loop
will do it later: set inputs -> do one step -> read outputs -> repeat.

Usage:
    python modelica/step_fmu.py modelica/SimpleTank.fmu
    python modelica/step_fmu.py modelica/HeatPumpTank.fmu
    python modelica/step_fmu.py modelica/HeatPumpTank.fmu 8760   (a whole year, to time it)

Build the FMUs first, see modelica/build_fmus.sh.
The input/output names are guessed from the FMU itself, so the same script
works for both test models.
"""
import sys
import time

import matplotlib.pyplot as plt
import pandas as pd
from fmpy import read_model_description, extract
from fmpy.fmi2 import FMU2Slave

fmu_path = sys.argv[1] if len(sys.argv) > 1 else "modelica/SimpleTank.fmu"
hours = int(sys.argv[2]) if len(sys.argv) > 2 else 48
step = 3600.0  # one hour in seconds

md = read_model_description(fmu_path)
vr = {v.name: v.valueReference for v in md.modelVariables}
inputs = [v.name for v in md.modelVariables if v.causality == "input"]
outputs = [v.name for v in md.modelVariables if v.causality == "output"]
print("inputs: ", inputs)
print("outputs:", outputs)

unzipdir = extract(fmu_path)
fmu = FMU2Slave(guid=md.guid, unzipDirectory=unzipdir,
                modelIdentifier=md.coSimulation.modelIdentifier,
                instanceName="plant")
fmu.instantiate()
fmu.setupExperiment(startTime=0.0)
fmu.enterInitializationMode()
fmu.exitInitializationMode()


def schedule(hour):
    """A made-up 'plan': heat pump runs at night when power is cheap,
    the process draws heat during the day shift. Returns every input any
    of the test models might want; only the ones the FMU has get used."""
    h = hour % 24
    hp_on = h < 6 or h >= 22
    return {
        "Q_hp_W": 1_000_000.0 if hp_on else 0.0,       # SimpleTank: heat in directly
        "y_hp": 1.0 if hp_on else 0.0,                 # HeatPumpTank: compressor signal
        "Q_draw_W": 600_000.0 if 7 <= h < 19 else 100_000.0,
        "T_amb_degC": 12 + 8 * ((h - 4) % 24 > 8),     # crude: 12 C at night, 20 C by day
    }


rows = []
t = 0.0
t0 = time.time()
for hour in range(hours):
    plan = schedule(hour)
    for name in inputs:
        fmu.setReal([vr[name]], [plan[name]])
    fmu.doStep(currentCommunicationPoint=t, communicationStepSize=step)
    t += step
    row = {"hour": hour + 1}
    row.update({name: plan[name] for name in inputs})
    for name in outputs:
        row[name] = fmu.getReal([vr[name]])[0]
    rows.append(row)

fmu.terminate()
fmu.freeInstance()
print(f"stepped {hours} hours in {time.time() - t0:.2f} s of wall clock")

df = pd.DataFrame(rows).set_index("hour")
print(df.round(1).to_string())

fig, ax = plt.subplots(2, 1, sharex=True, figsize=(9, 6))
heat_cols = [c for c in df.columns if c.startswith("Q_")]
(df[heat_cols] / 1000).plot(ax=ax[0], drawstyle="steps-post")
ax[0].set_ylabel("kW")
df[[c for c in outputs if c.startswith("T_")]].plot(ax=ax[1])
ax[1].set_ylabel("degC")
ax[1].set_xlabel("hour")
plt.tight_layout()
out_png = "notes/images/" + fmu_path.split("/")[-1].replace(".fmu", f"_{hours}h.png")
plt.savefig(out_png, dpi=90)
print("saved", out_png)
