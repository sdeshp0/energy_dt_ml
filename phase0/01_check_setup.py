"""
Step 1: does everything import, and are the keys there?

    python phase0/01_check_setup.py
"""
import importlib
import shutil
import sys

sys.path.insert(0, ".")
import config  # noqa: E402

print("python", sys.version.split()[0])

# phase 0 needs these. The later ones (pypsa, tespy, nixtla) are checked
# too, just so we know early if something won't install.
packages = ["numpy", "pandas", "matplotlib", "loadcast", "pvlib", "gridstatus", "fmpy",
            "pypsa", "tespy", "statsforecast", "mlforecast", "lightgbm"]
for name in packages:
    try:
        mod = importlib.import_module(name)
        print(f"  ok       {name:14s} {getattr(mod, '__version__', '?')}")
    except Exception as e:  # import errors come in many shapes
        print(f"  MISSING  {name:14s} ({type(e).__name__}: {e})")

print()
print("NREL key set:  ", bool(config.NREL_API_KEY))
print("NREL email set:", bool(config.NREL_EMAIL))
print("docker found:  ", bool(shutil.which("docker")), "(only needed for the Modelica test)")
print("data folder:   ", config.DATA_DIR)
