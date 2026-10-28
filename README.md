# energy_dt_ml

A side project: a digital twin of a (made-up) food processing plant in
Fresno, CA, that needs process heat and electricity. The plan is to mix
physics models, ML forecasting and optimization, and see what actually
helps:

- **loadcast** makes the plant's heat / cold / electricity demand
- **pvlib** + NREL NSRDB weather for rooftop PV
- **CAISO** day-ahead prices and grid CO2 (via **gridstatus**)
- a **Modelica** heat pump + hot water tank (Buildings Library), exported as
  an FMU and run from Python with **FMPy**, as the "real plant"
- **Nixtla** forecasters and **PyPSA** for scheduling (later phases)

I'm learning the modelling side as I go, so there's an
[experiment log](notes/experiment_log.md) with what I tried, including the
stuff that didn't work.

## Status

- [x] **Phase 0**: environment, data pulls, Modelica FMU test
- [ ] Phase 1: site model (PV, heat pump COP, simple tank, battery)
- [ ] Phase 2: PyPSA scheduling with perfect foresight
- [ ] Phase 3: forecasting (naive vs statistical vs LightGBM)
- [ ] Phase 4: Modelica plant in the loop

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then put your NREL API key + email in it
python phase0/01_check_setup.py
```

Free NREL API key: https://developer.nlr.gov/signup/ (NREL's developer site
moved from developer.nrel.gov).

## Phase 0 scripts

Run from the repo root, in order. All the site settings (location, year,
plant size, price node) are in [`config.py`](config.py).

| script | what it does | needs |
|---|---|---|
| `phase0/01_check_setup.py` | checks imports and keys | |
| `phase0/02_demand_loadcast.py` | a year of demand + experiments on loadcast's settings | |
| `phase0/03_weather_nsrdb.py` | a year of weather for Fresno + rough PV check | NREL key |
| `phase0/04_prices_caiso.py` | CAISO day-ahead hourly prices (slow, month by month) | |
| `phase0/05_co2_caiso.py` | hourly grid CO2 from the CAISO fuel mix (slow) | |

Data goes into `data/` (not in git, just re-run the scripts).

## Modelica FMU test

Needs Docker. OpenModelica runs in a container so nothing else to install.

```bash
# one time: get the Modelica libraries (next to this repo, not inside it)
mkdir -p ../mlibs && cd ../mlibs
git clone --depth 1 --branch v4.1.0  https://github.com/modelica/ModelicaStandardLibrary.git msl
git clone --depth 1 --branch v14.0.0 https://github.com/lbl-srg/modelica-buildings.git buildings
cd -

bash modelica/build_fmus.sh                            # builds SimpleTank.fmu and HeatPumpTank.fmu
python modelica/step_fmu.py modelica/HeatPumpTank.fmu  # steps it hourly for 48 h, saves a plot
```

## Layout

```
config.py            site settings, used by every script
phase0/              data pulls and setup checks
modelica/            plant models (.mo), build script, FMU stepping script
notes/               experiment log and plots
data/                downloaded/generated data (git-ignored)
```
