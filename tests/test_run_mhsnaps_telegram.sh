#!/bin/bash

# Test script for run_mhsnaps_telegram.sh

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to print test results
print_result() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓ $2${NC}"
    else
        echo -e "${RED}✗ $2${NC}"
        exit 1
    fi
}

# Get the directory where the test script is located
TEST_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$TEST_DIR")"

# Test 1: Check if the script exists
if [ -f "${PROJECT_ROOT}/run_mhsnaps_telegram.sh" ]; then
    print_result 0 "Script file exists"
else
    print_result 1 "Script file does not exist"
fi

# Test 2: Check if the script is executable
if [ -x "${PROJECT_ROOT}/run_mhsnaps_telegram.sh" ]; then
    print_result 0 "Script is executable"
else
    print_result 1 "Script is not executable"
fi

# Test 3: Check if required directories exist
if [ -d "${PROJECT_ROOT}/configs" ]; then
    print_result 0 "Configs directory exists"
else
    print_result 1 "Configs directory does not exist"
fi

if [ -d "${PROJECT_ROOT}/logs" ]; then
    print_result 0 "Logs directory exists"
else
    print_result 1 "Logs directory does not exist"
fi

# Test 4: Check if virtual environment exists
if [ -d "${PROJECT_ROOT}/venv" ]; then
    print_result 0 "Virtual environment exists"
else
    print_result 1 "Virtual environment does not exist"
fi

# Test 5: Run the script and check if it creates a log file
"${PROJECT_ROOT}/run_mhsnaps_telegram.sh"
if [ -f "${PROJECT_ROOT}/logs/run_mhsnaps_telegram.log" ]; then
    print_result 0 "Log file was created"
else
    print_result 1 "Log file was not created"
fi

# Test 6: Check if log file has content
if [ -s "${PROJECT_ROOT}/logs/run_mhsnaps_telegram.log" ]; then
    print_result 0 "Log file has content"
else
    print_result 1 "Log file is empty"
fi

# Print log file contents for debugging
echo -e "\nLog file contents:"
cat "${PROJECT_ROOT}/logs/run_mhsnaps_telegram.log"

echo -e "\nAll tests completed!" 