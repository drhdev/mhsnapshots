#!/bin/bash

# run_mhsnaps_telegram.sh
# Version: 0.1          
# Author: drhdev
# License: GPL v3
#
# Description:
# This script runs mhsnapshots.py and log2telegram.py in sequence.
# It is designed to be run from cron jobs.

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Create logs directory if it doesn't exist
mkdir -p "${SCRIPT_DIR}/logs"

# Activate the virtual environment
source "${SCRIPT_DIR}/venv/bin/activate"

# Clear the log file
> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"

# Run mhsnapshots.py with all YAML files from configs directory
echo "=== Starting mhsnapshots.py ===" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
python3 "${SCRIPT_DIR}/src/mhsnapshots.py" "${SCRIPT_DIR}/configs/"*.yaml >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log" 2>&1
MHSNAPS_EXIT_CODE=$?

# If mhsnapshots.py was successful, run log2telegram.py
if [ $MHSNAPS_EXIT_CODE -eq 0 ]; then
    echo -e "\n=== Starting log2telegram.py ===" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
    python3 "${SCRIPT_DIR}/src/log2telegram.py" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log" 2>&1
    LOG2TELEGRAM_EXIT_CODE=$?
    
    # Add final status to the log
    echo -e "\n=== Script Execution Summary ===" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
    echo "mhsnapshots.py exit code: $MHSNAPS_EXIT_CODE" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
    echo "log2telegram.py exit code: $LOG2TELEGRAM_EXIT_CODE" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
else
    echo -e "\n=== Script Execution Summary ===" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
    echo "mhsnapshots.py failed with exit code: $MHSNAPS_EXIT_CODE" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
    echo "log2telegram.py was not executed due to mhsnapshots.py failure" >> "${SCRIPT_DIR}/logs/run_mhsnaps_telegram.log"
fi

# Deactivate the virtual environment
deactivate 