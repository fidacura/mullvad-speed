# mullvad-scout 🚀

A CLI tool to find the best Mullvad VPN servers for your location

## What it does

- 📡 Fetches all available Mullvad WireGuard servers
- ⚡ Tests connection times to each server
- 📊 Shows you the top 10 fastest servers with their info:
  - Hostname
  - Location
  - IPv4 address
  - Ping time
  - Port speed
  - Whether it's owned by Mullvad
  - Available features (IPv6, SOCKS, MultiHop, etc.)

## Installation

```bash
# clone the repo
git clone https://github.com/fidacura/mullvad-scout.git
cd mullvad-scout

# create and activate venv
python -m venv venv
source venv/bin/activate

# install deps
pip install -r requirements.txt
```

## Usage

```bash
# show top 10 servers (default)
python mullvad_speed.py

# or test a specific no. of servers
python mullvad_speed.py 15  # shows top 15 servers
```

## Tips

- 🔍 Run the tool at different times of day to find consistently good servers
- 🌍 The closest server isn't always the fastest
- 💻 Look for Mullvad-owned servers if privacy is a priority
- 🚦 Consider server load during peak hours
