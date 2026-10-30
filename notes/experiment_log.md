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
