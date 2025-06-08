#!/usr/bin/env python3
# mhsnapshots.py
# Version: 0.2.3
# Author: drhdev
# License: GPL v3
#
# Description:
# This script manages snapshots for multiple Hetzner Cloud servers, including creation, retention, and deletion.
# Configuration is handled via YAML files located in the 'configs' subfolder, allowing individual settings per server.

import subprocess
import logging
from logging.handlers import RotatingFileHandler
import datetime
import os
import sys
import yaml
import time
import argparse
from dataclasses import dataclass
from typing import List, Optional

# Constants
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIGS_DIR = os.path.join(PROJECT_ROOT, "configs")
LOGS_DIR = os.path.join(PROJECT_ROOT, "logs")
DEFAULT_CONFIG_FILE = os.path.join(CONFIGS_DIR, "config.yaml")
LOG_FILE = os.path.join(LOGS_DIR, "mhsnapshots.log")
DELAY_BETWEEN_SERVERS = 5  # seconds

@dataclass
class ServerConfig:
    id: str
    name: str
    api_token: str
    retain_last_snapshots: int

class SnapshotManager:
    def __init__(self, config_paths: List[str], verbose: bool = False):
        self.config_paths = config_paths
        self.verbose = verbose
        self.setup_logging()  # Set up logging first
        self.servers = self.load_configs()
        self.hcloud_path = self.get_hcloud_path()
        if not self.hcloud_path:
            self.error_exit("hcloud command not found. Please ensure it is installed and accessible.")

    def load_configs(self) -> List[ServerConfig]:
        servers = []
        for path in self.config_paths:
            full_path = os.path.join(CONFIGS_DIR, path)
            if not os.path.exists(full_path):
                self.error_exit(f"Configuration file '{full_path}' does not exist.")
            try:
                with open(full_path, 'r') as f:
                    config = yaml.safe_load(f)
                if 'server' not in config:
                    self.error_exit(f"Configuration file '{full_path}' is missing the 'server' key.")
                server = config['server']
                # Validate required fields
                required_fields = ['id', 'name', 'api_token', 'retain_last_snapshots']
                for field in required_fields:
                    if field not in server:
                        self.error_exit(f"Configuration file '{full_path}' is missing the '{field}' field under 'server'.")
                servers.append(ServerConfig(
                    id=server['id'],
                    name=server['name'],
                    api_token=server['api_token'],
                    retain_last_snapshots=int(server['retain_last_snapshots'])
                ))
            except yaml.YAMLError as e:
                self.error_exit(f"Error parsing YAML file '{full_path}': {e}")
            except ValueError as ve:
                self.error_exit(f"Invalid data type in '{full_path}': {ve}")
        if not servers:
            self.error_exit("No valid server configurations found.")
        return servers

    def get_hcloud_path(self) -> Optional[str]:
        """
        Find the hcloud CLI executable in common installation locations.
        Checks PATH first, then common installation directories.
        """
        # Common installation paths for different operating systems
        common_paths = [
            "/usr/local/bin/hcloud",  # macOS, Linux
            "/usr/bin/hcloud",        # Linux
            "/opt/homebrew/bin/hcloud",  # macOS ARM
            os.path.expanduser("~/.local/bin/hcloud"),  # User's local bin
            os.path.expanduser("~/bin/hcloud"),  # User's bin
        ]

        # First try to find hcloud in PATH
        try:
            # Use 'where' on Windows, 'which' on Unix-like systems
            command = "where hcloud" if os.name == 'nt' else "which hcloud"
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            path = result.stdout.decode().strip()
            if path and os.path.exists(path):
                self.logger.debug(f"Found hcloud in PATH: {path}")
                return path
        except subprocess.CalledProcessError:
            pass

        # If not found in PATH, check common installation locations
        for path in common_paths:
            if os.path.exists(path):
                self.logger.debug(f"Found hcloud in common path: {path}")
                return path

        # If still not found, try to find it in the current directory
        current_dir = os.path.dirname(os.path.abspath(__file__))
        local_path = os.path.join(current_dir, "hcloud")
        if os.path.exists(local_path):
            self.logger.debug(f"Found hcloud in current directory: {local_path}")
            return local_path

        self.logger.error("hcloud CLI not found in PATH or common installation locations")
        return None

    def setup_logging(self):
        self.logger = logging.getLogger('mhsnapshots.py')
        self.logger.setLevel(logging.DEBUG)
        # Ensure logs directory exists
        os.makedirs(LOGS_DIR, exist_ok=True)
        # Delete existing log file if it exists
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
        # Use FileHandler to create new log file
        handler = logging.FileHandler(LOG_FILE, mode='w')
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        if self.verbose:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)

    def error_exit(self, message: str):
        if hasattr(self, 'logger'):
            self.logger.error(message)
        else:
            print(f"ERROR: {message}", file=sys.stderr)
        sys.exit(1)

    def run_command(self, command: str, api_token: str) -> Optional[str]:
        masked_token = api_token[:6] + '...' + api_token[-6:]
        masked_command = command.replace(api_token, masked_token)
        self.logger.info(f"Executing command: {masked_command}")
        try:
            env = os.environ.copy()
            env["HCLOUD_TOKEN"] = api_token
            result = subprocess.run(command.split(), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
            stdout = result.stdout.decode().strip()
            stderr = result.stderr.decode().strip()
            self.logger.debug(f"Command stdout: {stdout}")
            if stderr:
                self.logger.warning(f"Command stderr: {stderr}")
            return stdout
        except subprocess.CalledProcessError as e:
            stdout = e.stdout.decode().strip() if e.stdout else ""
            stderr = e.stderr.decode().strip() if e.stderr else ""
            self.logger.error(f"Command failed: {stderr}")
            self.logger.debug(f"Failed command output: {stdout}")
            return None

    def get_snapshots(self, server: ServerConfig) -> List[dict]:
        command = f"{self.hcloud_path} image list --type snapshot --output json"
        snapshots_output = self.run_command(command, server.api_token)
        snapshots = []

        if snapshots_output:
            try:
                import json
                snapshots_data = json.loads(snapshots_output)
                for snap in snapshots_data:
                    # Check if this snapshot belongs to our server
                    if snap.get('created_from', {}).get('id') == int(server.id):
                        try:
                            created_at = datetime.datetime.fromisoformat(snap['created'].replace('Z', '+00:00')).astimezone(datetime.timezone.utc)
                            snapshots.append({
                                "id": str(snap['id']),
                                "name": snap['description'],  # Use description as name
                                "created_at": created_at
                            })
                            self.logger.debug(f"Server '{server.name}': Snapshot found: {snap['description']} (ID: {snap['id']}) created at {created_at}")
                        except ValueError as ve:
                            self.logger.error(f"Server '{server.name}': Invalid date format for snapshot '{snap['description']}': {snap['created']}")
            except json.JSONDecodeError as je:
                self.logger.error(f"Server '{server.name}': Failed to parse snapshot data: {je}")
        else:
            self.logger.error(f"Server '{server.name}': No snapshots retrieved or an error occurred during retrieval.")

        return snapshots

    def identify_snapshots_to_delete(self, server: ServerConfig, snapshots: List[dict], retain: int) -> List[dict]:
        snapshots.sort(key=lambda x: x['created_at'], reverse=True)
        to_delete = snapshots[retain:]
        self.logger.info(f"Server '{server.name}': Identified {len(to_delete)} snapshot(s) for deletion: {[snap['name'] for snap in to_delete]}")
        return to_delete

    def wait_for_snapshot_ready(self, server: ServerConfig, snapshot_id: str, max_wait_time: int = 300) -> bool:
        """
        Wait for a snapshot to be ready (available) before proceeding.
        Returns True if the snapshot is ready, False if it times out.
        """
        start_time = time.time()
        while time.time() - start_time < max_wait_time:
            command = f"{self.hcloud_path} image describe {snapshot_id} --output json"
            result = self.run_command(command, server.api_token)
            if result:
                try:
                    import json
                    snapshot_data = json.loads(result)
                    if snapshot_data.get('status') == 'available':
                        self.logger.info(f"Server '{server.name}': Snapshot {snapshot_id} is now available.")
                        return True
                    self.logger.debug(f"Server '{server.name}': Snapshot {snapshot_id} status: {snapshot_data.get('status')}")
                except json.JSONDecodeError:
                    self.logger.error(f"Server '{server.name}': Failed to parse snapshot status data.")
            time.sleep(10)  # Check every 10 seconds
        self.logger.error(f"Server '{server.name}': Snapshot {snapshot_id} did not become available within {max_wait_time} seconds.")
        return False

    def create_snapshot(self, server: ServerConfig) -> Optional[str]:
        timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        snapshot_name = f"{server.name}-{timestamp}"
        command = f"{self.hcloud_path} server create-image --type snapshot --description {snapshot_name} {server.id}"
        result = self.run_command(command, server.api_token)
        if result:
            # Extract snapshot ID from the result
            try:
                snapshot_id = result.split()[1]  # Format: "Image 123456789 created from Server 123456"
                if self.wait_for_snapshot_ready(server, snapshot_id):
                    self.logger.info(f"Server '{server.name}': New snapshot created: {snapshot_name}")
                    return snapshot_name
                else:
                    self.logger.error(f"Server '{server.name}': Snapshot creation timed out.")
                    return None
            except (IndexError, ValueError) as e:
                self.logger.error(f"Server '{server.name}': Failed to extract snapshot ID from result: {e}")
                return None
        else:
            self.logger.error(f"Server '{server.name}': Failed to create a new snapshot.")
            return None

    def delete_snapshots(self, server: ServerConfig, snapshots: List[dict]):
        for snap in snapshots:
            command = f"{self.hcloud_path} image delete {snap['id']}"
            result = self.run_command(command, server.api_token)
            if result is not None:
                self.logger.info(f"Server '{server.name}': Snapshot deleted: {snap['name']}")
            else:
                self.logger.error(f"Server '{server.name}': Failed to delete snapshot: {snap['name']}")

    def write_final_status(self, server: ServerConfig, snapshot_name: str, total_snapshots: int, status: str):
        hostname = os.uname().nodename
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_status_message = f"FINAL_STATUS | mhsnapshots.py | {server.name} | {status.upper()} | {hostname} | {timestamp} | {snapshot_name} | {total_snapshots} snapshots exist"
        self.logger.info(final_status_message)

    def manage_snapshots_for_server(self, server: ServerConfig):
        self.logger.info(f"--- Managing server '{server.name}' (ID: {server.id}) ---")
        self.logger.info(f"Configuration: Retain last {server.retain_last_snapshots} snapshot(s). New snapshots will be named as '{server.name}-<timestamp>'.")

        # Retrieve existing snapshots
        snapshots = self.get_snapshots(server)
        self.logger.info(f"Server '{server.name}': Found {len(snapshots)} existing snapshot(s).")

        # Create a new snapshot
        snapshot_name = self.create_snapshot(server)

        # Get updated snapshot list after creation
        updated_snapshots = self.get_snapshots(server)
        self.logger.info(f"Server '{server.name}': Found {len(updated_snapshots)} snapshot(s) after creation.")

        # Sort snapshots by creation date (newest first)
        updated_snapshots.sort(key=lambda x: x['created_at'], reverse=True)

        # Keep only the most recent snapshots as specified in retain_last_snapshots
        snapshots_to_keep = updated_snapshots[:server.retain_last_snapshots]
        snapshots_to_delete = updated_snapshots[server.retain_last_snapshots:]

        if snapshots_to_delete:
            self.logger.info(f"Server '{server.name}': Identified {len(snapshots_to_delete)} snapshot(s) for deletion: {[snap['name'] for snap in snapshots_to_delete]}")
            self.delete_snapshots(server, snapshots_to_delete)
        else:
            self.logger.info(f"Server '{server.name}': No snapshots to delete based on retention policy.")

        # Get final snapshot count
        final_snapshots = self.get_snapshots(server)
        total_snapshots = len(final_snapshots)

        # Write final status to the log
        if snapshot_name:
            status = "success"
        else:
            status = "failure"
        self.write_final_status(server, snapshot_name if snapshot_name else "none", total_snapshots, status)

        self.logger.info(f"--- Completed snapshot management for server '{server.name}' ---\n")

    def run(self):
        for idx, server in enumerate(self.servers):
            try:
                self.manage_snapshots_for_server(server)
                if idx < len(self.servers) - 1:
                    self.logger.info(f"Waiting for {DELAY_BETWEEN_SERVERS} seconds before processing the next server...")
                    time.sleep(DELAY_BETWEEN_SERVERS)
            except Exception as e:
                self.logger.error(f"An unexpected error occurred for server '{server.name}': {e}")

def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Manage snapshots for multiple Hetzner Cloud servers.")
    parser.add_argument(
        'configs',
        nargs='*',
        help=f"YAML configuration files for servers located in the '{CONFIGS_DIR}' directory. Defaults to all .yaml files in the directory if not specified."
    )
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help="Enable verbose logging to the console."
    )
    return parser.parse_args()

def main():
    args = parse_arguments()
    
    # If no config files specified, use all .yaml files in the configs directory
    if not args.configs:
        args.configs = [f for f in os.listdir(CONFIGS_DIR) if f.endswith('.yaml')]
        if not args.configs:
            print(f"Error: No .yaml configuration files found in the '{CONFIGS_DIR}' directory.", file=sys.stderr)
            sys.exit(1)

    manager = SnapshotManager(args.configs, args.verbose)
    manager.run()

if __name__ == "__main__":
    main()
