# Experiment log

Running notes on what I tried, what worked and what didn't. The details
(code, plots, tables) are in the notebooks; this is the short version.

---

## Phase 0: learning the tools

| notebook | status | headline |
|---|---|---|
| 01 loadcast | ✅ | 1 MW heat pump is too small for this demand |
| 02 pvlib | ✅ (clear-sky weather) | ~1,750 kWh/kWp with losses; ModelChain and by-hand disagree until you know about the 14% PVWatts losses |
| 03 TESPy | ✅ | R1233zd(E) works for 90 °C; R134a and propane don't; online tutorials use an old API |
| 04 PyPSA | ✅ (made-up prices) | a hot water tank is the big win; the electricity tariff decides heat pump vs boiler |
| 05 sizing calculator | ✅ (made-up prices) | sliders + "let PyPSA size it"; gas price and grid charges decide everything |

### Environment

- **Didn't work:** installing everything unpinned. pip pulled pandas 3.1
  (newest PyPSA needs it) but gridstatus needs pandas 2.x. pip only warns.
- **Worked:** `pandas<3` and `pypsa<1.3` (1.2 is the last that accepts
  pandas 2). `pip check` is clean on Python 3.13.
- NREL and CAISO servers weren't reachable when I ran the notebooks, so
  02 uses clear-sky weather and 04 uses a made-up price. Everything else
  is real.

### 01 loadcast

- Base case (10 GWh/yr, semi-continuous): heat averages 805 kW, peaks at
  2,006 kW. Flat across the year because loadcast has no weather in it.
- Process classes: batch peaks at 3.6 MW and idles 60% of the year;
  continuous never drops below 10% of peak. Sticking with semi-continuous.
- **`carrier_correlation` can't go below ~0.46.** Above 0.5 you get exactly
  what you ask for. Below that loadcast warns that the carriers share one
  shift calendar. A correlation sweep should start at 0.5.
- Changing the seed keeps annual energy identical but the hours only
  correlate 0.47. Handy for "train on one year, test on another".
- **1 MW heat pump is too small:** it would need to run 80% of the year
  just to keep up, and demand is above 1 MW for 2,366 hours.

### 02 pvlib

- Clear-sky (no clouds ever) gives ~2,000 kWh/kWp by hand. Real Fresno
  should be a bit lower, so re-run with NSRDB.
- **Didn't work:** `ModelChain.with_pvwatts` without
  `temperature_model_parameters` errors out ("Could not infer temperature
  model").
- **Confusing:** ModelChain gave 1,745 vs 2,004 by hand. Not the
  temperature model like I first thought; it's PVWatts' default ~14%
  system losses. With `losses_model="no_loss"` they're within 2%.
- West-facing makes 20% less energy but doubles the share after 4 pm
  (8% → 17%). Whether that pays depends on prices.
- Single-axis tracking: +14%. **Gotcha:** tracker angles are NaN at night
  and silently shrink the total if you don't fill them.
- Cells reach ~58 °C in summer (with made-up temperatures).

### 03 TESPy

- **Didn't work:** `Network(T_unit="C", ...)` from every tutorial. TESPy
  0.11 wants `nw.units.set_defaults(...)`.
- Simplest heat pump (90 °C condensing, 5 °C evaporating): COP 2.39 with
  R1233zd(E), 418 kW of compressor power per MW of heat.
- Refrigerant sweep, condensing 60-105 °C:
  - R134a and R290 (propane) **fail above ~100 °C**: past their critical
    points.
  - R1234ze(Z) **fails at -10 °C evaporating**, but the error says
    CoolProp's model for it stops at 273 K. A data limit, not physics.
  - Ammonia has the best COP but needs ~57 bar at 95 °C.
  - R1233zd(E) and R245fa work everywhere at ~10 bar. Using R1233zd(E).
- TESPy prints long tracebacks for every failed point; I turned its
  logger down.
- COP map at 90 °C condensing: 1.9 at -5 °C outside, 4.1 at 45 °C.
- **"Fraction of Carnot" shortcut:** best fit 0.57, mean error 3%, worst
  8% at the edges. Good enough as a fallback; using the map itself.
- Left out for now: superheat, subcooling, water/air heat exchangers,
  part load. Real COPs will be lower.

### 04 PyPSA (perfect foresight, full year, made-up prices)

| case | annual cost | heat pump share |
|---|---|---|
| no storage | $183k | 88% |
| + 4 MWh tank | $148k | 99% |
| + 12 MWh tank | $136k | 100% |
| + 1 MWh battery (no tank) | $152k | 92% |
| tank + battery | $120k | 99% |

- **The tank is the big win** (-19%).
- **I don't trust the battery result.** The made-up price swings ~$90/MWh
  every day and goes negative. The battery also raises peak grid import from
  1,147 to 1,647 kW, which would hurt with a demand charge (not modelled
  yet).
- PV gets curtailed when prices go negative, because there's no export in
  the model and importing pays.
- Heat pump size: 1.5 MW is the knee. "1.5 MW at average COP" is only
  ~1.2 MW on a cold morning.
- **No boiler → infeasible** unless the heat pump is 2 MW *and* there's a
  tank. An infeasible LP doesn't say which hour broke. Next time: add an
  expensive "unmet heat" generator.
- **The tariff decides heat pump vs boiler.** At wholesale prices the heat
  pump does 99% of the heat, with +$0.04/kWh about half, and with
  +$0.10/kWh about a third. A real PG&E industrial tariff is the most
  important missing input.
- A full year solves in ~2 s with HiGHS.

### 05 Sizing calculator

Sliders for heat pump, tank, battery, PV, grid charges, gas price and
demand charge. Calculator mode compares your design with "gas boiler only"
(yearly cost, upfront cost, payback). Sizing mode lets PyPSA pick the sizes,
paying a yearly share of each one's installed cost (rough guesses: heat pump
$700/kW, tank $25/kWh, battery $400/kWh, PV $1,600/kWp, 7% over their
lifetimes).

- **Didn't work: too slow.** A full-year sizing run took 25-50 s. Useless
  with sliders.
- **Fix: model every 4th week** (13 weeks, still hourly), each hour counted
  ~4 times. Now ~6 s per run (including the business-as-usual comparison).
- **Didn't work at first: the shortcut broke the storage.** I weighted every
  hour by 4 everywhere, including the storage equations, so each hour of
  charging counted as 4 hours. The tank came out at 0.5 MWh instead of 2.9.
  Fix: weight costs and energy by 4, but keep storage at 1. After that the
  shortcut matches the full year closely (heat pump 930 vs 928 kW, tank
  3.0 vs 2.9 MWh).
- Equipment slider widgets in ipywidgets 8 need keyword arguments
  (`IntSlider(value=..., min=..., ...)`); positional ones throw a
  confusing `TypeError`.

What sizing mode picks (made-up prices):

| prices | heat pump | tank | battery | PV |
|---|---|---|---|---|
| wholesale only | 930 kW | 3.0 MWh | 0 | 0 |
| + $0.06/kWh grid charges | 0 | 0 | 0 | 94 kWp |
| + $0.06/kWh and $20/kW-month demand charge | 0 | 0 | 730 kWh | 300 kWp |
| cheap gas ($4/MMBtu) | 0 | 0 | 0 | 0 |
| expensive gas ($14/MMBtu) | 1,180 kW | 5.0 MWh | 0 | 0 |
| cheap batteries ($150/kWh) | 850 kW | 2.1 MWh | 2.4 MWh | 0 |

- The default design in the calculator (1.5 MW heat pump, 4 MWh tank,
  1 MWp PV) **doesn't pay off**: ~18-year payback. Mostly the PV: each kWp
  costs ~$137/yr but its energy is worth ~$70 at wholesale prices (lowest
  exactly when the sun is out).
- Grid charges on top of wholesale kill the heat pump. What matters is the
  spark spread (electricity vs gas price), not the COP alone.
- A demand charge is what makes a battery (and some PV) worth it. Cheap
  batteries get bought for price arbitrage instead, and then peak grid
  import goes UP to 2.1 MW.
- The demand charge here is the year's peak × 12, which overstates a real
  monthly-peak tariff.

### Parked: Modelica

I first tried a Modelica (Buildings Library) heat pump + tank exported as
an FMU. It worked in the end, but it was a lot of toolchain fighting
(OpenModelica version, initialization, solver settings) for a learning
phase, so it's out for now. It's in the git history if I come back to it.

---

## Things to decide in phase 1
- Real weather (NREL key) and real CAISO prices
- A real PG&E industrial tariff with demand charges
- Heat pump ~1.5 MW plus a gas boiler, or bigger and no boiler?
- Add an "unmet heat" slack so infeasible cases still solve
- Monthly demand charges instead of year-peak × 12
- Better equipment cost numbers (these are guesses)
