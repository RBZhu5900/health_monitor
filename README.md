# Xiaomi Health Data Fetcher

## Features

- Daily authentication with Mi Fit API
- Retrieve health metrics (steps, distance, calories, sleep, etc.)
- Simple JSON configuration
- Minimal dependencies (only requests required)

## Quick Start

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure your credentials:

```json
// data/config.json
{
  "username": "YOUR_XIAOMI_ACCOUNT",
  "password": "YOUR_PASSWORD"
}
```

3. Execute the script:

```bash
python src/main.py
```

## Notes

- Requires valid Xiaomi account credentials
- Uses official Mi Fit API endpoints
- Designed for single daily execution
- Stores no persistent data locally
- Outlook email has disabled basic authentication, you need OAuth2.0 to send email
