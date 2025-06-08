#!/bin/bash

# Script to run mhsnapshots.py and log2telegram.py in sequence
# This script is designed to be run from cron jobs

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "${SCRIPT_DIR}/logs"

# Activate the virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# Run mhsnapshots.py with all YAML files from configs directory
# Redirect output to log file, overwriting any existing log
python3 "${SCRIPT_DIR}/src/mhsnapshots.py" "${SCRIPT_DIR}/configs/"*.yaml > "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log" 2>&1

# Run log2telegram.py
# Append output to the same log file
python3 "${SCRIPT_DIR}/src/log2telegram.py" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log" 2>&1

# Deactivate the virtual environment
deactivate 