# Health Monitor

A health monitoring system based on Zepp(Mi Fit) data, providing data collection, analysis, and health advice.

## Features

- Automatic collection of Zepp(Mi Fit) data
- AI-powered health data analysis and recommendations
- Email notifications and daily health reports
- Web interface for configuration management
- Automated scheduled tasks
- Docker containerized deployment

## Requirements

- Python 3.9+
- Docker (optional, for containerized deployment)

## Quick Start

### Local Development

1. Clone the repository:

```bash
git clone https://github.com/RBZhu5900/health-monitor.git
cd health-monitor
```

2. Create virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Configure:

```bash
cp data/config.example.json data/config.json
# Edit config.json with your settings
```

5. Run:

```bash
python src/app.py
```

### Docker Deployment

1. Build image:

```bash
docker build -t health-monitor:latest .
```

2. Run container:

```bash
docker run -d \
  --name health-monitor \
  -p 5050:5050 \
  -v $(pwd)/data/config.json:/app/data/config.json \
  -v $(pwd)/data_export:/app/data_export \
  -v $(pwd)/logs:/app/logs \
  health-monitor:latest
```

## Configuration

The `config.json` file contains the following settings:

```json
{
  "username": "your_username", // Xiaomi Sport account
  "password": "your_password", // Xiaomi Sport password
  "deepseek": {
    "api_key": "your_api_key", // DeepSeek API key
    "base_url": "your_deepseek_api_base_url", // DeepSeek API base URL
    "model": "your_deepseek_model" // DeepSeek model name
  },
  "smtp": {
    "server": "smtp.example.com", // SMTP server address
    "port": 587, // SMTP server port
    "sender_email": "your_email@example.com", // Sender email address
    "sender_password": "your_app_password" // Email app password or authorization code
  },
  "receiver_email": "target@example.com", // Recipient email address
  "health": {
    "step_goal": 8000, // Daily step goal
    "sleep_hours": {
      "min": 7, // Minimum sleep hours
      "max": 8 // Maximum sleep hours
    },
    "deep_sleep_ratio": 0.2 // Recommended deep sleep ratio
  }
}
```

## Features Description

### Automated Tasks

- Fetch health data at 3 AM daily
- Send health report at 8 AM daily
- Send reminders based on AI recommendations at specific times

### Web Interface

- Access management interface at `http://localhost:5050`
- Modify account settings
- Update email configuration
- Manually trigger data collection
- Download health reports

## Project Structure

```
health_monitor/
├── data/                 # Configuration files
│   ├── config.json
│   └── config.example.json
├── src/                  # Source code
│   ├── app.py           # Main entry
│   ├── main.py          # Background service
│   ├── web_app.py       # Web service
│   ├── templates/       # Frontend templates
│   └── services/        # Business services
├── data_export/         # Data export directory
├── logs/                # Log directory
├── requirements.txt     # Dependencies
├── Dockerfile          # Docker configuration
└── .dockerignore      # Docker ignore file
```

## Logging

- Application logs are located in `logs/health_monitor.log`
- In Docker environment, use `docker logs health-monitor` to view logs

## Troubleshooting

1. Email Sending Failure

   - Verify SMTP configuration
   - Check email authorization code validity
   - Review logs for detailed error information

2. Data Collection Failure
   - Verify Xiaomi account credentials
   - Check network connectivity
   - Review logs for detailed error information

## License

[MIT License](LICENSE)
