#!/usr/bin/env python3
# log2telegram.py
# Version: 0.4.1
# Author: drhdev
# License: GPLv3
#
# Description:
# This script checks the 'mhsnapshots.log' file for FINAL_STATUS entries,
# sends them as formatted messages via Telegram, and then exits.
# It introduces a configurable delay between sending multiple
# Telegram messages to avoid overwhelming the Telegram API.

import os
import sys
import logging
import requests
import argparse
import re
import time
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

# Constants
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
LOG_FILE_PATH = os.path.join(LOGS_DIR, "mhsnapshots.log")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# Validate Telegram credentials
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set as environment variables.")
    sys.exit(1)

def setup_logging():
    logger = logging.getLogger('log2telegram.py')
    logger.setLevel(logging.DEBUG)
    # Ensure logs directory exists
    os.makedirs(LOGS_DIR, exist_ok=True)
    # Delete existing log file if it exists
    log_file = os.path.join(LOGS_DIR, "log2telegram.log")
    if os.path.exists(log_file):
        os.remove(log_file)
    # Use FileHandler to create new log file
    handler = logging.FileHandler(log_file, mode='w')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger

def setup_console_logging(verbose: bool):
    """
    Sets up console logging if verbose is True.
    """
    if verbose:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        logger.debug("Console logging enabled.")

# Compile regex for FINAL_STATUS detection (flexible matching)
FINAL_STATUS_PATTERN = re.compile(r'^FINAL_STATUS\s*\|', re.IGNORECASE)

def send_telegram_message(message, retries=3, delay_between_retries=5):
    """
    Sends the given message to Telegram with a retry mechanism.
    """
    formatted_message = format_message(message)
    logger.debug(f"Formatted message to send: {formatted_message}")
    for attempt in range(1, retries + 1):
        try:
            payload = {
                "chat_id": TELEGRAM_CHAT_ID,
                "text": formatted_message,
                "parse_mode": "Markdown"  # Using Markdown for better formatting
            }
            response = requests.post(TELEGRAM_API_URL, data=payload, timeout=10)
            logger.debug(f"Telegram API response: {response.status_code} - {response.text}")
            if response.status_code == 200:
                logger.info(f"Sent Telegram message: {formatted_message}")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Exception occurred while sending Telegram message: {e}")
        if attempt < retries:
            logger.info(f"Retrying in {delay_between_retries} seconds... (Attempt {attempt}/{retries})")
            time.sleep(delay_between_retries)
    logger.error(f"Failed to send Telegram message after {retries} attempts.")
    return False

def format_message(raw_message):
    """
    Formats the raw FINAL_STATUS log entry into a Markdown message for Telegram.
    Example Input:
        FINAL_STATUS | mhsnapshots.py | example.com | SUCCESS | hostname | 2024-12-02 13:32:34 | example.com-20241202133213 | 3 snapshots exist
    Example Output:
        *FINAL_STATUS*
        *Script:* `mhsnapshots.py`
        *Server:* `example.com`
        *Status:* `SUCCESS`
        *Hostname:* `hostname`
        *Timestamp:* `2024-12-02 13:32:34`
        *Snapshot:* `example.com-20241202133213`
        *Total Snapshots:* `3 snapshots exist`
    """
    parts = raw_message.split(" | ")
    if len(parts) != 8:
        logger.warning(f"Unexpected FINAL_STATUS format: {raw_message}")
        return raw_message  # Return as is if format is unexpected

    _, script_name, server_name, status, hostname, timestamp, snapshot_name, snapshot_info = parts

    formatted_message = (
        f"*FINAL_STATUS*\n"
        f"*Script:* `{script_name}`\n"
        f"*Server:* `{server_name}`\n"
        f"*Status:* `{status}`\n"
        f"*Hostname:* `{hostname}`\n"
        f"*Timestamp:* `{timestamp}`\n"
        f"*Snapshot:* `{snapshot_name}`\n"
        f"*Total Snapshots:* `{snapshot_info}`"
    )
    return formatted_message

def process_log(delay_between_messages: int):
    """
    Processes the log file for FINAL_STATUS entries and sends them via Telegram.
    Introduces a delay between sending multiple messages to avoid overwhelming Telegram.
    """
    if not os.path.exists(LOG_FILE_PATH):
        logger.error(f"Log file '{LOG_FILE_PATH}' does not exist.")
        return

    try:
        with open(LOG_FILE_PATH, 'r') as f:
            lines = f.readlines()
            if not lines:
                logger.info("No lines to process.")
                return

            logger.info(f"Processing {len(lines)} line(s).")
            final_status_entries = []
            for line_number, line in enumerate(lines, start=1):
                original_line = line  # Keep the original line for debugging
                line = line.strip()

                # Check if the line contains the delimiter ' - '
                if " - " not in line:
                    logger.debug(f"Line {line_number}: Skipping non-formatted line.")
                    continue  # Skip lines without the expected format

                # Split the log line into components
                split_line = line.split(" - ", 2)  # Split into 3 parts: timestamp, level, message
                if len(split_line) < 3:
                    logger.warning(f"Malformed log line (less than 3 parts): {original_line.strip()}")
                    continue  # Skip malformed lines

                message_part = split_line[2]  # The actual log message

                if FINAL_STATUS_PATTERN.match(message_part):
                    final_status_entries.append((line_number, message_part))
                else:
                    logger.debug(f"Line {line_number}: No FINAL_STATUS entry found.")
                    logger.debug(f"Processed Line {line_number}: {message_part}")  # Log the actual message content

            if final_status_entries:
                logger.info(f"Detected {len(final_status_entries)} FINAL_STATUS entry(ies) to send.")
                for idx, (line_number, message) in enumerate(final_status_entries, start=1):
                    logger.debug(f"Line {line_number}: Detected FINAL_STATUS entry.")
                    success = send_telegram_message(message)
                    if not success:
                        logger.error(f"Failed to send Telegram message for line {line_number}: {message}")
                    if idx < len(final_status_entries):
                        logger.debug(f"Waiting for {delay_between_messages} seconds before sending the next message.")
                        time.sleep(delay_between_messages)
            else:
                logger.info("No FINAL_STATUS entries detected to send.")

            logger.info(f"Processed {len(final_status_entries)} FINAL_STATUS entry(ies).")

    except Exception as e:
        logger.error(f"Error processing log file: {e}")

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Monitor 'mhsnapshots.log' for FINAL_STATUS entries and send them to Telegram.")
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output to the console.')
    parser.add_argument('-d', '--delay', type=int, default=10, help='Delay in seconds between sending multiple Telegram messages (default: 10 seconds).')
    args = parser.parse_args()

    # Set up console logging if verbose is enabled
    setup_console_logging(args.verbose)

    # Process the log file with the specified delay
    process_log(args.delay)

if __name__ == "__main__":
    logger = setup_logging()
    main()

