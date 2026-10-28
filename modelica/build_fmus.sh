#!/usr/bin/env bash
# Build both test FMUs with OpenModelica running in Docker, so nothing needs
# installing except Docker itself.
#
# Needs the Modelica libraries cloned next to this repo first:
#   mkdir -p ../mlibs && cd ../mlibs
#   git clone --depth 1 --branch v4.1.0  https://github.com/modelica/ModelicaStandardLibrary.git msl
#   git clone --depth 1 --branch v14.0.0 https://github.com/lbl-srg/modelica-buildings.git buildings
#
# Run from the repo root:  bash modelica/build_fmus.sh
set -e
LIBS="$(cd "$(dirname "$0")/../.." && pwd)/mlibs"
OMC_IMAGE=openmodelica/openmodelica:v1.26.3-minimal   # 1.25 can't read Buildings v14, see log

cd "$(dirname "$0")"
for script in export_simple_tank.mos export_heat_pump_tank.mos; do
  echo "=== $script ==="
  # the grep hides OpenModelica complaining that it can't reach its online
  # package index, which we don't need since the libraries are mounted
  docker run --rm -v "$LIBS":/libs:ro -v "$PWD":/work -w /work "$OMC_IMAGE" \
    omc "$script" 2>&1 | grep -v "libraries.openmodelica.org"
done
ls -la *.fmu
