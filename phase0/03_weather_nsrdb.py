"""
Step 3: download a year of weather for the site from NREL's NSRDB.

    python phase0/03_weather_nsrdb.py

Needs NREL_API_KEY and NREL_EMAIL in .env (see .env.example).
Saves data/weather_nsrdb_<year>.csv and does a rough PV sanity check.

NOTE: NREL was renamed "National Laboratory of the Rockies" and the API moved
to developer.nlr.gov. pvlib 0.16 already uses the new address. If you have
an older pvlib and get connection errors, upgrade it.
"""
import sys

import matplotlib.pyplot as plt
import pandas as pd
import pvlib

sys.path.insert(0, ".")
import config  # noqa: E402

if not config.NREL_API_KEY or not config.NREL_EMAIL:
    sys.exit("Put NREL_API_KEY and NREL_EMAIL in a .env file first (see .env.example)")

out = config.DATA_DIR / f"weather_nsrdb_{config.YEAR}.csv"

if out.exists():
    print("already downloaded, reading", out)
    weather = pd.read_csv(out, index_col=0, parse_dates=True)
else:
    try:
        # a real year, so it lines up with the CAISO prices for that year
        weather, meta = pvlib.iotools.get_nsrdb_psm4_aggregated(
            config.LATITUDE, config.LONGITUDE,
            config.NREL_API_KEY, config.NREL_EMAIL,
            year=config.YEAR, time_step=60, leap_day=True)
        source = f"NSRDB PSM4 aggregated {config.YEAR}"
    except Exception as e:
        # the newest year is sometimes not published yet; fall back to the
        # typical meteorological year so we at least have something
        print(f"year {config.YEAR} failed ({e}), trying TMY instead")
        weather, meta = pvlib.iotools.get_nsrdb_psm4_tmy(
            config.LATITUDE, config.LONGITUDE,
            config.NREL_API_KEY, config.NREL_EMAIL)
        source = "NSRDB PSM4 TMY (NOT a real year, don't line it up with prices)"
        out = config.DATA_DIR / "weather_nsrdb_tmy.csv"

    print("source:", source)
    print("site metadata:", {k: meta.get(k) for k in ["Latitude", "Longitude", "Elevation", "Time Zone"]})
    weather.index.name = "time"
    weather.to_csv(out)
    print("saved", out)

print(weather.columns.tolist())
# Check the timestamps! NSRDB hourly values have been stamped at hh:30 in
# older versions (the middle of the hour). Everything else in this project
# is stamped at the start of the hour, so look at the minutes here.
print("first timestamps:", list(weather.index[:3]))
print(weather.describe().T[["mean", "min", "max"]].round(1))

# ---------------------------------------------------------------
# Rough PV sanity check: 1 MWp, fixed tilt, PVWatts-style model.
# Fresno should come out somewhere around 1,700-2,000 kWh per kWp per year.
# If it's way off, the timestamps or units are probably wrong.
# ---------------------------------------------------------------
loc = pvlib.location.Location(config.LATITUDE, config.LONGITUDE)
solpos = loc.get_solarposition(weather.index)
poa = pvlib.irradiance.get_total_irradiance(
    surface_tilt=25, surface_azimuth=180,
    solar_zenith=solpos.apparent_zenith, solar_azimuth=solpos.azimuth,
    dni=weather.dni, ghi=weather.ghi, dhi=weather.dhi)
temp_cell = pvlib.temperature.faiman(poa.poa_global, weather.temp_air, weather.wind_speed)
pdc = pvlib.pvsystem.pvwatts_dc(poa.poa_global, temp_cell, pdc0=1000, gamma_pdc=-0.004)  # kW, 1 MWp
pac = pvlib.inverter.pvwatts(pdc, pdc0=1000 / 0.96).clip(lower=0)

print(f"\nPV check: {pac.sum() / 1000:.0f} kWh/kWp per year (expect ~1700-2000 for Fresno)")

# Is the timing right? Peak PV should be close to solar noon (~12:00 in
# local standard time). If it peaks at 4 am the time zone is off.
print("hour of day with highest average PV:", pac.groupby(pac.index.hour).mean().idxmax())

week = slice(f"{config.YEAR}-06-16", f"{config.YEAR}-06-22")
fig, ax = plt.subplots(2, 1, sharex=True, figsize=(10, 5))
weather.loc[week, ["ghi", "dni", "dhi"]].plot(ax=ax[0])
ax[0].set_ylabel("W/m2")
pac.loc[week].plot(ax=ax[1], label="PV AC (1 MWp)")
ax[1].set_ylabel("kW")
plt.tight_layout()
plt.savefig(config.IMG_DIR / "weather_pv_week.png", dpi=90)
print("saved plot")
