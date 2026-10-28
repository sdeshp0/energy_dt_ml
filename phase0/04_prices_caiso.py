"""
Step 4: download a year of CAISO day-ahead hourly prices for our node.

    python phase0/04_prices_caiso.py

No key needed. Goes month by month and saves each month as it goes, because
CAISO's OASIS API is slow and rate-limited, and I didn't want to lose a
half-finished year when it times out. Re-running skips months already saved.

Saves data/prices_caiso_<year>.csv  ($/MWh, hourly, local standard time)
"""
import sys
import time
import warnings

import gridstatus
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, ".")
import config  # noqa: E402

# gridstatus marks get_lmp() as deprecated in favour of
# get_lmp_day_ahead_hourly(), but that one downloads EVERY node in CAISO
# (thousands). get_lmp() still lets us ask for just one node.
warnings.filterwarnings("ignore", category=DeprecationWarning)

caiso = gridstatus.CAISO()
cache_dir = config.DATA_DIR / "caiso_lmp_months"
cache_dir.mkdir(exist_ok=True)

for month in range(1, 13):
    f = cache_dir / f"{config.YEAR}-{month:02d}.csv"
    if f.exists():
        continue
    start = pd.Timestamp(config.YEAR, month, 1)
    end = start + pd.offsets.MonthBegin(1)
    print(f"downloading {start:%Y-%m} ...", flush=True)
    for attempt in range(3):
        try:
            df = caiso.get_lmp(date=start, end=end, market="DAY_AHEAD_HOURLY",
                               locations=[config.CAISO_PRICE_NODE], sleep=5)
            df.to_csv(f, index=False)
            break
        except Exception as e:
            print(f"  failed ({e}), waiting and trying again")
            time.sleep(30)
    else:
        print(f"  gave up on {start:%Y-%m}, re-run the script later")

# ---- stitch the months together ----
months = sorted(cache_dir.glob(f"{config.YEAR}-*.csv"))
raw = pd.concat([pd.read_csv(f) for f in months])
print("columns from gridstatus:", raw.columns.tolist())

# CAISO times come with a UTC offset; convert to our local standard time
# so they line up with the NSRDB weather (no daylight saving jumps).
raw["time"] = pd.to_datetime(raw["Interval Start"], utc=True).dt.tz_convert(config.TIMEZONE)
prices = (raw.set_index("time")[["LMP", "Energy", "Congestion", "Loss", "GHG"]]
          .sort_index())
prices = prices[~prices.index.duplicated()]
prices = prices.rename(columns={"LMP": "price_usd_per_mwh"})

# ---- checks ----
expected = pd.date_range(f"{config.YEAR}-01-01", f"{config.YEAR + 1}-01-01",
                         freq="h", inclusive="left", tz=config.TIMEZONE)
missing = expected.difference(prices.index)
print(f"\nhours: {len(prices)} of {len(expected)}, missing {len(missing)}")
if len(missing):
    print("first few missing:", list(missing[:5]))
    # fill small gaps by carrying the price forward; flag it in the log if big
    prices = prices.reindex(expected).ffill()

print(prices["price_usd_per_mwh"].describe().round(1))
print("hours with negative prices:", (prices.price_usd_per_mwh < 0).sum())

out = config.DATA_DIR / f"prices_caiso_{config.YEAR}.csv"
prices.to_csv(out)
print("saved", out)

# ---- the famous duck curve: average price by hour of day, per season ----
p = prices.price_usd_per_mwh
season = p.index.month.map({12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring",
                            5: "spring", 6: "summer", 7: "summer", 8: "summer",
                            9: "fall", 10: "fall", 11: "fall"})
ax = p.groupby([season, p.index.hour]).mean().unstack(0).plot(
    figsize=(8, 4), title=f"CAISO day-ahead price by hour, {config.CAISO_PRICE_NODE}")
ax.set_xlabel("hour of day (local standard time)")
ax.set_ylabel("$/MWh")
plt.tight_layout()
plt.savefig(config.IMG_DIR / "prices_by_hour.png", dpi=90)
print("saved plot")
