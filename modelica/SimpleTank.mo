// Experiment 1: the simplest possible "tank" model, using only the
// Modelica Standard Library. Just here to check that the FMU export
// pipeline works at all before trying the Buildings Library.
//
// One fully mixed tank (a single heat capacity), heat pump heat in,
// process heat out, and a small loss to ambient.
model SimpleTank
  parameter Real volume_m3 = 40 "about 4 MWh between 40 and 90 degC";
  parameter Real UA_W_per_K = 200 "tank heat loss coefficient";
  parameter Real T_start_degC = 60;

  Modelica.Blocks.Interfaces.RealInput Q_hp_W "heat pump heat into the tank";
  Modelica.Blocks.Interfaces.RealInput Q_draw_W "process heat taken out";
  Modelica.Blocks.Interfaces.RealOutput T_tank_degC;

  Modelica.Thermal.HeatTransfer.Components.HeatCapacitor tank(
    C = volume_m3 * 1000 * 4186,
    T(start = T_start_degC + 273.15, fixed = true));
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow hp;
  Modelica.Thermal.HeatTransfer.Sources.PrescribedHeatFlow draw;
  Modelica.Thermal.HeatTransfer.Components.ThermalConductor loss(G = UA_W_per_K);
  Modelica.Thermal.HeatTransfer.Sources.FixedTemperature ambient(T = 293.15);
  Modelica.Blocks.Math.Gain minus(k = -1);
equation
  connect(Q_hp_W, hp.Q_flow);
  connect(Q_draw_W, minus.u);
  connect(minus.y, draw.Q_flow);
  connect(hp.port, tank.port);
  connect(draw.port, tank.port);
  connect(tank.port, loss.port_a);
  connect(loss.port_b, ambient.port);
  T_tank_degC = tank.T - 273.15;
end SimpleTank;
