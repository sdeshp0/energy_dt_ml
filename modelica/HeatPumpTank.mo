// Experiment 2: heat pump + stratified hot water tank using the
// Modelica Buildings Library (v14.0.0). This is the "real plant" that the
// optimizer will eventually steer.
//
// Charging loop:  tank bottom -> pump -> heat pump condenser -> tank top
// Load loop:      tank top -> pump -> process (takes Q_draw_W) -> tank bottom
// Evaporator:     a water/brine loop that arrives at outdoor temperature
//                  (stand-in for an air coil, see experiment log)
//
// Inputs from Python:  y_hp (0..1 compressor signal), Q_draw_W, T_amb_degC
// Outputs to Python:   tank temperatures, heat delivered, electric power
//
// I kept every component on its default settings unless I had a reason to
// change it. No graphical annotations, since I wrote this by hand.
model HeatPumpTank
  package Water = Buildings.Media.Water;

  // ---- sizes (same as the proposal's starting values) ----
  parameter Real Q_hp_nominal_W = 1e6 "heat pump thermal output at y=1";
  parameter Real V_tank_m3 = 70 "about 4 MWh between 40 and 90 degC";
  parameter Real h_tank_m = 6;
  parameter Integer nSeg = 8 "tank layers";
  parameter Real T_start_degC = 60;

  // ---- heat pump performance (Carnot efficiency approach) ----
  parameter Real etaCarnot = 0.45 "fraction of the ideal Carnot COP";
  parameter Real TCon_nom_K = 273.15 + 85;
  parameter Real TEva_nom_K = 273.15 + 10;
  parameter Real COP_nom = etaCarnot * TCon_nom_K / (TCon_nom_K - TEva_nom_K);
  parameter Real dTCon = 10 "condenser water temperature rise";
  parameter Real dTEva = -5 "source temperature drop across evaporator";
  parameter Real m_con_nom = Q_hp_nominal_W / 4186 / dTCon;
  parameter Real m_src_nom = Q_hp_nominal_W * (1 - 1/COP_nom) / 4186 / (-dTEva);

  // ---- load loop ----
  parameter Real m_load_nom = 15 "kg/s, gives about 10 K drop at 600 kW";

  // ---- the process needs hot enough water; below this it gets less heat ----
  parameter Real T_supply_min_degC = 50;

  // ---- safety: stop the heat pump if the top of the tank gets too hot ----
  parameter Real T_max_degC = 90;
  parameter Real T_restart_degC = 85;

  // ---------------- inputs / outputs ----------------
  Modelica.Blocks.Interfaces.RealInput y_hp(min = 0, max = 1) "compressor signal from the optimizer";
  Modelica.Blocks.Interfaces.RealInput Q_draw_W "process heat demand";
  Modelica.Blocks.Interfaces.RealInput T_amb_degC "outdoor air temperature";

  Modelica.Blocks.Interfaces.RealOutput T_top_degC;
  Modelica.Blocks.Interfaces.RealOutput T_mid_degC;
  Modelica.Blocks.Interfaces.RealOutput T_bot_degC;
  Modelica.Blocks.Interfaces.RealOutput Q_hp_W "heat delivered by the heat pump";
  Modelica.Blocks.Interfaces.RealOutput P_hp_W "electric power of the heat pump";
  Modelica.Blocks.Interfaces.RealOutput y_actual "compressor signal after the safety cut-out";
  Modelica.Blocks.Interfaces.RealOutput Q_delivered_W "process heat actually delivered";
  Modelica.Blocks.Interfaces.RealOutput Q_unmet_W "process heat we could not deliver";

  // ---------------- components ----------------
  Buildings.Fluid.Storage.Stratified tank(
    redeclare package Medium = Water,
    m_flow_nominal = m_con_nom,
    VTan = V_tank_m3, hTan = h_tank_m, dIns = 0.1, nSeg = nSeg,
    T_start = T_start_degC + 273.15);

  Buildings.Fluid.HeatPumps.Carnot_y heaPum(
    redeclare package Medium1 = Water,
    redeclare package Medium2 = Water,
    P_nominal = Q_hp_nominal_W / COP_nom,
    use_eta_Carnot_nominal = true,
    etaCarnot_nominal = etaCarnot,
    TCon_nominal = TCon_nom_K,
    TEva_nominal = TEva_nom_K,
    dTCon_nominal = dTCon,
    dTEva_nominal = dTEva,
    dp1_nominal = 10000, dp2_nominal = 10000,
    T1_start = T_start_degC + 273.15,
    T2_start = 273.15 + 10,
    energyDynamics = Modelica.Fluid.Types.Dynamics.FixedInitial);

  Buildings.Fluid.Movers.FlowControlled_m_flow pumCha(
    redeclare package Medium = Water,
    m_flow_nominal = m_con_nom,
    nominalValuesDefineDefaultPressureCurve = true,
    use_riseTime = false) "charging pump, flow follows the compressor signal";

  Buildings.Fluid.Movers.FlowControlled_m_flow pumLoa(
    redeclare package Medium = Water,
    m_flow_nominal = m_load_nom,
    inputType = Buildings.Fluid.Types.InputType.Constant,
    nominalValuesDefineDefaultPressureCurve = true,
    use_riseTime = false) "load pump, always on";

  Buildings.Fluid.HeatExchangers.HeaterCooler_u process(
    redeclare package Medium = Water,
    m_flow_nominal = m_load_nom,
    dp_nominal = 5000,
    Q_flow_nominal = -1) "takes Q_draw_W out of the water";

  Buildings.Fluid.Sources.Boundary_pT expVes(redeclare package Medium = Water, nPorts = 1)
    "expansion vessel, sets the pressure";

  Buildings.Fluid.Sources.MassFlowSource_T srcIn(
    redeclare package Medium = Water, use_T_in = true, m_flow = m_src_nom, nPorts = 1);
  Buildings.Fluid.Sources.Boundary_pT srcOut(redeclare package Medium = Water, nPorts = 1);

  Modelica.Blocks.Logical.Hysteresis tooHot(uLow = T_restart_degC, uHigh = T_max_degC);

  // the charging pump never fully stops, so the heat pump always sees some flow
  Real pump_flow;

equation
  // safety cut-out on the top of the tank
  tooHot.u = T_top_degC;
  y_actual = if tooHot.y then 0 else max(0, min(1, y_hp));
  heaPum.y = y_actual;
  pump_flow = m_con_nom * max(0.05, y_actual);
  pumCha.m_flow_in = pump_flow;

  // process heat demand (negative = cooling the water). If the top of the
  // tank is too cold the process only gets part of what it asked for, fading
  // out over 5 K. Without this the model happily pulled heat out of a cold
  // tank until the water "froze" and the solver crashed.
  Q_delivered_W = max(0, Q_draw_W) * min(1, max(0, (T_top_degC - T_supply_min_degC) / 5));
  Q_unmet_W = max(0, Q_draw_W) - Q_delivered_W;
  process.u = Q_delivered_W;

  // heat source at outdoor temperature (kept above freezing for the water model)
  srcIn.T_in = max(T_amb_degC, 2) + 273.15;

  // charging loop
  connect(tank.port_b, pumCha.port_a);
  connect(expVes.ports[1], pumCha.port_a);
  connect(pumCha.port_b, heaPum.port_a1);
  connect(heaPum.port_b1, tank.port_a);

  // load loop (uses the side ports of the top and bottom layers)
  connect(tank.fluPorVol[1], pumLoa.port_a);
  connect(pumLoa.port_b, process.port_a);
  connect(process.port_b, tank.fluPorVol[nSeg]);

  // evaporator source loop
  connect(srcIn.ports[1], heaPum.port_a2);
  connect(heaPum.port_b2, srcOut.ports[1]);

  // outputs
  T_top_degC = tank.vol[1].T - 273.15;
  T_mid_degC = tank.vol[integer(nSeg / 2)].T - 273.15;
  T_bot_degC = tank.vol[nSeg].T - 273.15;
  Q_hp_W = heaPum.QCon_flow;
  P_hp_W = heaPum.P;

  annotation(experiment(StopTime = 172800, Interval = 3600));
end HeatPumpTank;
