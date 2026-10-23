#!/usr/bin/env bash
set -euo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"
# Python hash randomization is fixed before starting the interpreter.
export PYTHONHASHSEED="${PYTHONHASHSEED:-42}"
# Limit nested BLAS/OpenMP parallelism inside the eight pipeline workers.
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export OPENBLAS_NUM_THREADS="${OPENBLAS_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export NUMEXPR_NUM_THREADS="${NUMEXPR_NUM_THREADS:-1}"
if [[ ! -x "$repo_root/.venv/bin/python" ]]; then
  echo 'Create the project .venv with Poetry first; see docs/proxmox-campaigns.md.' >&2
  exit 1
fi
exec "$repo_root/.venv/bin/python" -m experiments.campaign "$@"
