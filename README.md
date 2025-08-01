# DNS View Synchronization Tool

A Python script for bi-directional synchronization of DNS A records between two Infoblox Universal DDI views.

## Overview

This tool synchronizes DNS A records between two views (e.g., AZURE-3 and AZURE-9) within the same DNS zone. It prevents sync loops and handles conflicts.

**Note: This is a Minimum Viable Product (MVP). No support or warranty is provided.**

## Features

- Bi-directional sync between two DNS views
- Loop prevention using detailed comment markers
- Conflict detection and resolution
- logging with timestamps

## Installation

```bash
# Clone the repository
cd dns-sync

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the configuration template:
```bash
cp config.py.example config.py
```

2. Edit `config.py` with your settings:
```python
# Infoblox API Configuration
INFOBLOX_API_URL = "https://csp.infoblox.com"
INFOBLOX_API_TOKEN = "your_api_token_here"

# DNS Views to synchronize
DNS_VIEW_SOURCE = "AZURE-3"
DNS_VIEW_TARGET = "AZURE-9"

# DNS Zone to synchronize (note the trailing dot)
DNS_ZONE_NAME = "privatelink.blob.core.windows.net."
```

## Usage

Run synchronization:
```bash
python3 sync_dns_zones.py
```

## Configuration Parameters

| Setting | Description | Example |
|---------|-------------|---------|
| `INFOBLOX_API_URL` | API endpoint | `https://csp.infoblox.com` |
| `INFOBLOX_API_TOKEN` | API token with DNS permissions | `your_token_here` |
| `DNS_VIEW_SOURCE` | Source DNS view name | `AZURE-3` |
| `DNS_VIEW_TARGET` | Target DNS view name | `AZURE-9` |
| `DNS_ZONE_NAME` | Zone to sync (with trailing dot) | `privatelink.blob.core.windows.net.` |

## How It Works

1. **Fetch Records**: Retrieves A records from both views
2. **Compare**: Identifies differences between views
3. **Sync**: Creates missing records in each view
4. **Loop Prevention**: Uses detailed comment markers to prevent infinite loops

### Sync Comments

Records include detailed metadata:
```
Synced from AZURE-3 on 2025-08-01 13:00:25 UTC, created: 2025-07-15T10:30:00Z
```

### Example Output

```
2025-08-01 13:00:24,329 - INFO - Starting DNS Zone Synchronization
2025-08-01 13:00:24,329 - INFO - Views: AZURE-3 ↔ AZURE-9
2025-08-01 13:00:25,666 - INFO - Created 20vms01stor: 10.10.10.5
2025-08-01 13:00:27,854 - INFO - Records synced AZURE-3→AZURE-9: 3
2025-08-01 13:00:27,854 - INFO - Total records synced: 5
```

## Automation

For regular synchronization, add to crontab:

```bash
# Run every 5 minutes
*/5 * * * * cd /path/to/dns-sync && python3 sync_dns_zones.py >> /var/log/dns-sync.log 2>&1
```

## Troubleshooting

**Configuration Not Found**
- Copy `config.py.example` to `config.py`
- Update with your API token and view names

**Authentication Failed**
- Verify API token is valid and has DNS permissions

**View Not Found**
- Check view names are correct (case-sensitive)
- Verify views exist in Infoblox system

**Zone Not Found**
- Ensure zone name has trailing dot: `example.com.`
- Verify zone exists in both views

## Requirements

- Python 3.7+
- `requests` library
- Valid Infoblox Universal DDI API access

## Limitations

- Only synchronizes A records (IPv4)
- Does not delete records (create/update only)
- Manual conflict resolution required for simultaneous changes
- Single API token (both views must be accessible with same token)

## Project Structure

```
dns-sync/
├── README.md              # This documentation
├── requirements.txt       # Python dependencies
├── sync_dns_zones.py     # Main synchronization script
├── test_connection.py    # Configuration test script
├── config.py.example     # Configuration template
├── config.py             # Your configuration (create from template)
└── .gitignore           # Git ignore rules
```

## Disclaimer

This is a Minimum Viable Product (MVP) provided as-is without any support, warranty, or guarantees. Use at your own risk.