# energy_dt_ml

A side project: an energy model of a (made-up) food processing plant in
Fresno, CA, that needs process heat and electricity. The plan is to combine
physics models, ML forecasting and optimization and see what actually
helps.

I know the energy side but I'm learning the modelling tools as I go, so
phase 0 is just notebooks: one per tool, poking at it in a controlled way.
The [experiment log](notes/experiment_log.md) has what I tried, including
the stuff that didn't work.

## Phase 0 notebooks

Run them in order. Each one saves a small CSV to `data/` that the next one
uses.

| notebook | tool | what I'm figuring out |
|---|---|---|
| [01_loadcast](notebooks/01_loadcast.ipynb) | [loadcast](https://github.com/Matt-haug/loadcast) | what the plant's heat / cold / electricity demand looks like, and what the settings do |
| [02_pvlib](notebooks/02_pvlib.ipynb) | [pvlib](https://pvlib-python.readthedocs.io) | how much PV a Fresno rooftop makes, and when |
| [03_tespy](notebooks/03_tespy.ipynb) | [TESPy](https://tespy.readthedocs.io) | heat pump COP vs outdoor temperature, which refrigerants work |
| [04_pypsa](notebooks/04_pypsa.ipynb) | [PyPSA](https://pypsa.org) | a year of cheapest operation using all of the above, plus storage and sizing experiments |

**Heads up:** the committed notebooks were run without access to NREL or
CAISO, so the weather is a clear-sky model and the electricity price is a
made-up duck curve. Both are clearly labelled in the notebooks. With an
NREL key (and `DOWNLOAD_PRICES = True` in notebook 04) they use real data.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # optional: NREL API key + email for real weather
jupyter lab
```

Free NREL API key: https://developer.nlr.gov/signup/ (NREL's developer site
moved from developer.nrel.gov).

All the site settings (location, year, plant size, price node) are in
[`config.py`](config.py).

## Status

- [x] **Phase 0**: learn the tools in notebooks
- [ ] Phase 1: site model (fix sizes, real prices and weather, tariff)
- [ ] Phase 2: scheduling with perfect foresight vs simple rules
- [ ] Phase 3: forecasting (naive vs statistical vs LightGBM)
