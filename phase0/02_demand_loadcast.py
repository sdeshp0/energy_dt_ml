"""
Step 2: make a year of site demand with loadcast and look at it.

    python phase0/02_demand_loadcast.py

Saves data/demand_loadcast.csv (heat, cold, elec in kW, hourly).

Also runs a couple of quick experiments to see how the knobs change the
profiles, because I wanted to understand them before trusting them.
"""
import sys

import loadcast
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, ".")
import config  # noqa: E402


def make_demand(process_class=config.PROCESS_CLASS,
                correlation=config.CARRIER_CORRELATION,
                seed=42):
    return loadcast.generate(
        year=config.YEAR,
        annual_mwh=config.ANNUAL_MWH,
        heat_to_cold=config.HEAT_TO_COLD,
        elec_share=config.ELEC_SHARE,
        process_class=process_class,
        carrier_correlation=correlation,
        seed=seed,
    )


# ---------------------------------------------------------------
# the base case
# ---------------------------------------------------------------
demand = make_demand()
demand = demand[["heat_kw", "cold_kw", "elec_kw"]]   # waste_kw is all zeros here
demand.index.name = "time"

print(demand.describe().round(1))
print("\nannual MWh:")
print((demand.sum() / 1000).round(0))
print("\nloadcast summary:")
print(loadcast.summary_table(demand).round(3))

out = config.DATA_DIR / "demand_loadcast.csv"
demand.to_csv(out)
print("\nsaved", out)

# a normal-looking week in spring
week = demand.loc[f"{config.YEAR}-04-07":f"{config.YEAR}-04-13"]
ax = week.plot(figsize=(10, 4), title="loadcast demand, one week in April")
ax.set_ylabel("kW")
plt.tight_layout()
plt.savefig(config.IMG_DIR / "demand_week.png", dpi=90)
plt.close()

# ---------------------------------------------------------------
# experiment A: what do the four process classes look like?
# ---------------------------------------------------------------
fig, axes = plt.subplots(4, 1, sharex=True, figsize=(10, 9))
rows = []
for ax, pc in zip(axes, loadcast.available_classes()):
    d = make_demand(process_class=pc)
    d.loc[f"{config.YEAR}-04-07":f"{config.YEAR}-04-13", ["heat_kw", "elec_kw"]].plot(ax=ax, legend=False)
    ax.set_title(pc, fontsize=9)
    ax.set_ylabel("kW")
    rows.append({"class": pc,
                 "heat_peak_kw": d.heat_kw.max(),
                 "heat_load_factor": d.heat_kw.mean() / d.heat_kw.max(),
                 "hours_heat_below_10pct": (d.heat_kw < 0.1 * d.heat_kw.max()).sum()})
axes[0].legend(["heat", "elec"], loc="upper right")
plt.tight_layout()
plt.savefig(config.IMG_DIR / "demand_process_classes.png", dpi=90)
plt.close()
print("\nexperiment A - process classes:")
print(pd.DataFrame(rows).round(2).to_string(index=False))

# ---------------------------------------------------------------
# experiment B: does carrier_correlation actually do what it says?
# measure the real hourly correlation between heat and elec
# ---------------------------------------------------------------
rows = []
for c in [0.0, 0.25, 0.5, 0.75, 0.95]:
    d = make_demand(correlation=c)
    rows.append({"asked_for": c,
                 "got_heat_vs_elec": d.heat_kw.corr(d.elec_kw),
                 "got_heat_vs_cold": d.heat_kw.corr(d.cold_kw)})
print("\nexperiment B - asked-for vs measured correlation:")
print(pd.DataFrame(rows).round(2).to_string(index=False))

# ---------------------------------------------------------------
# experiment C: same settings, different random seed
# (if the twin's "measured" demand is a different seed from the one the
# forecaster trained on, how different is it?)
# ---------------------------------------------------------------
a = make_demand(seed=42)
b = make_demand(seed=7)
print("\nexperiment C - seed 42 vs seed 7:")
print("  heat correlation between seeds:", round(a.heat_kw.corr(b.heat_kw), 2))
print("  annual heat MWh:", round(a.heat_kw.sum() / 1000), "vs", round(b.heat_kw.sum() / 1000))
