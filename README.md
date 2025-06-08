# mhsnapshots - Hetzner Cloud Snapshot Manager

A robust solution for managing snapshots of multiple Hetzner Cloud servers with Telegram notifications. This tool automatically creates, manages, and maintains snapshots for your Hetzner Cloud servers while keeping you informed through Telegram notifications.

## Features

- Automated snapshot creation and management for multiple Hetzner Cloud servers
- Configurable retention policy per server
- Real-time Telegram notifications for snapshot operations
- Detailed logging with rotation
- Support for multiple server configurations
- Cross-platform compatibility (Linux, macOS)

## Prerequisites

- Python 3.8 or higher
- Hetzner Cloud CLI (hcloud)
- A Hetzner Cloud account with API access
- A Telegram bot token and chat ID

### Installing Hetzner Cloud CLI on Ubuntu 22.04

1. Add the Hetzner Cloud repository:
```bash
curl -fsSL https://packages.hetzner.com/hetzner-cloud-cli/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hetzner-cloud-cli-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hetzner-cloud-cli-archive-keyring.gpg] https://packages.hetzner.com/hetzner-cloud-cli/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hetzner-cloud-cli.list
```

2. Update package list and install hcloud:
```bash
sudo apt update
sudo apt install hcloud-cli
```

3. Verify installation:
```bash
hcloud version
```

Note: The official hcloud CLI is built and released for Linux/macOS/Windows x86_64 and FreeBSD—but not directly for Raspberry Pi’s ARM architecture, so you won’t find a ready-made ARM binary for Raspbian/Ubuntu on Pi but you can ompile from source (Go). 

1.	Install Go (e.g. sudo apt install golang-go).

2.	Clone the CLI repo:
```bash
git clone https://github.com/hetznercloud/cli.git
cd cli
```

3.	Build the binary:
```bash
go build -o hcloud ./cmd/hcloud
```

4.	Move the executable into your PATH:
```bash
sudo mv hcloud /usr/local/bin/
hcloud version  # should run fine
```

This approach works flawlessly on ARM and gives you the latest features.

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/mhsnapshots.git
cd mhsnapshots
```

2. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install required Python packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the project root with your Telegram credentials:
```bash
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
```

## Configuration

### Server Configuration

1. Copy the example configuration file:
```bash
cp configs/config.yaml.example configs/your-server-name.yaml
```

2. Edit the configuration file with your server details:
```yaml
server:
  id: "123456"                    # Your Hetzner Cloud server ID
  name: "example-server"          # Server name (used for snapshot naming)
  api_token: "your-api-token"     # Your Hetzner Cloud API token
  retain_last_snapshots: 7        # Number of snapshots to retain
```

You can create multiple configuration files for different servers in the `configs` directory.

## Usage

### Manual Execution

Run the script manually:
```bash
./run_mhsnaps_telegram.sh
```

### Automated Execution with Cron

To run the script daily at 5 PM on Ubuntu 22.04:

1. Make the script executable:
```bash
chmod +x run_mhsnaps_telegram.sh
```

2. Edit your crontab:
```bash
crontab -e
```

3. Add the following line (adjust the path to match your installation):
```bash
0 17 * * * /path/to/mhsnapshots/run_mhsnaps_telegram.sh
```

## Project Structure

```
mhsnapshots/
├── configs/                    # Server configuration files
│   ├── config.yaml.example    # Example configuration
│   └── your-server-name.yaml  # Your server configurations
├── logs/                      # Log files directory
├── src/                       # Source code
│   ├── mhsnapshots.py        # Main snapshot management script
│   └── log2telegram.py       # Telegram notification script
├── venv/                      # Python virtual environment
├── .env                       # Environment variables
├── requirements.txt           # Python dependencies
└── run_mhsnaps_telegram.sh    # Main execution script
```

## How It Works

1. **Snapshot Creation**: The script creates a new snapshot for each configured server.
2. **Retention Management**: Old snapshots are deleted based on the retention policy.
3. **Logging**: All operations are logged to `logs/mhsnapshots.log`.
4. **Telegram Notifications**: The script sends notifications for each operation via Telegram.

### Log Format

The script generates detailed logs in the following format:
```
FINAL_STATUS | mhsnapshots.py | server-name | STATUS | hostname | timestamp | snapshot-name | total-snapshots
```

### Telegram Notifications

Notifications are sent in a formatted Markdown message containing:
- Script name
- Server name
- Operation status
- Hostname
- Timestamp
- Snapshot name
- Total snapshots

## Troubleshooting

### Common Issues

1. **hcloud command not found**
   - Ensure hcloud is properly installed
   - Verify the installation path is in your system's PATH

2. **Telegram notifications not working**
   - Check your `.env` file for correct credentials
   - Verify your Telegram bot token and chat ID
   - Ensure the bot is added to the chat

3. **Snapshot creation fails**
   - Verify your Hetzner Cloud API token
   - Check server ID and permissions
   - Ensure sufficient disk space

## License

This project is licensed under the GPL v3 License - see the LICENSE file for details.

