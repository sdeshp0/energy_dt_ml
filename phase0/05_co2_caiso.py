"""
Step 5: hourly grid CO2 intensity for CAISO, worked out from the fuel mix.

    python phase0/05_co2_caiso.py

CAISO publishes a 5-minute fuel mix (MW by fuel). There's no official
hourly CO2 factor for free, so this does the simple thing:

    CO2 [kg/MWh] = sum(MW of each fuel * emission factor) / sum(MW)

The emission factors are rough, see EMISSION_FACTORS below. Good enough for
"run the heat pump when the grid is clean", not for official reporting.

Saves data/co2_caiso_<year>.csv (kg CO2 per MWh, hourly, local standard time)
"""
import sys

import gridstatus
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, ".")
import config  # noqa: E402

# kg CO2 per MWh generated. Rough numbers:
#  - natural gas: CAISO's gas fleet is a mix of combined cycle (~370) and
#    peakers (~550+), so ~430 is a middle value
#  - imports: CARB's default for "unspecified" imports is 428
#  - biomass/biogas counted as zero (biogenic), which is debatable
EMISSION_FACTORS = {
    "Natural Gas": 430,
    "Coal": 1000,
    "Imports": 428,
    "Other": 430,      # unknown, assume gas-like
    "Biomass": 0,
    "Biogas": 0,
    "Geothermal": 0,
    "Nuclear": 0,
    "Large Hydro": 0,
    "Small Hydro": 0,
    "Solar": 0,
    "Wind": 0,
    # Batteries: left out on purpose. They are negative while charging and
    # just move other generation around in time.
}

caiso = gridstatus.CAISO()
cache_dir = config.DATA_DIR / "caiso_fuel_mix_months"
cache_dir.mkdir(exist_ok=True)

for month in range(1, 13):
    f = cache_dir / f"{config.YEAR}-{month:02d}.csv"
    if f.exists():
        continue
    start = pd.Timestamp(config.YEAR, month, 1)
    end = start + pd.offsets.MonthBegin(1)
    print(f"downloading fuel mix {start:%Y-%m} (one request per day, this is slow) ...", flush=True)
    try:
        df = caiso.get_fuel_mix(start, end=end)
        df.to_csv(f, index=False)
    except Exception as e:
        print(f"  failed ({e}), re-run the script later to pick it up")

months = sorted(cache_dir.glob(f"{config.YEAR}-*.csv"))
mix = pd.concat([pd.read_csv(f) for f in months])
print("fuel columns:", [c for c in mix.columns if c not in ("Time", "Interval Start", "Interval End")])

mix["time"] = pd.to_datetime(mix["Interval Start"], utc=True).dt.tz_convert(config.TIMEZONE)
mix = mix.set_index("time").sort_index()
mix = mix[~mix.index.duplicated()]

unknown = [c for c in mix.columns if c not in EMISSION_FACTORS
           and c not in ("Time", "Interval Start", "Interval End", "Batteries")]
if unknown:
    print("WARNING: no emission factor for", unknown, "- treated as zero")

fuels = [c for c in EMISSION_FACTORS if c in mix.columns]
gen = mix[fuels].clip(lower=0)          # MW, 5-minute
gen_hourly = gen.resample("h").mean()   # average MW over each hour = MWh

co2_t_per_h = sum(gen_hourly[f] * EMISSION_FACTORS[f] for f in fuels) / 1000
co2 = pd.DataFrame({
    "co2_kg_per_mwh": 1000 * co2_t_per_h / gen_hourly.sum(axis=1),
    "renewable_share": gen_hourly[[f for f in ["Solar", "Wind", "Geothermal", "Small Hydro",
                                               "Biomass", "Biogas"] if f in fuels]].sum(axis=1)
                       / gen_hourly.sum(axis=1),
})

print(co2.describe().round(2))
out = config.DATA_DIR / f"co2_caiso_{config.YEAR}.csv"
co2.to_csv(out)
print("saved", out)

c = co2.co2_kg_per_mwh
ax = c.groupby([c.index.month, c.index.hour]).mean().unstack(0).plot(
    figsize=(8, 4), title="CAISO grid CO2 by hour of day (one line per month)", legend=False)
ax.set_xlabel("hour of day (local standard time)")
ax.set_ylabel("kg CO2 / MWh")
plt.tight_layout()
plt.savefig(config.IMG_DIR / "co2_by_hour.png", dpi=90)
print("saved plot")
