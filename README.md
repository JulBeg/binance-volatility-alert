# Volatility Alert

A Python-based tool for monitoring and alerting on market volatility.

## Features

- Real-time volatility monitoring
- Configurable alert thresholds
- Historical volatility analysis

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/volatility-alert.git
cd volatility-alert
```

2. Configure environment variables in `.env.example` and rename it to `.env`:
```yaml
environment:
  - ALERT_THRESHOLD=5.0
  - CHECK_INTERVAL=300
  - QUOTE_CURRENCY=USDT
  - TELEGRAM_BOT_TOKEN=your_bot_token
  - TELEGRAM_CHAT_ID=your_chat_id
```

3. Run with Docker Compose:
```bash
docker-compose up
```

## Upcoming Features

- Add price decrease alerts

## License

MIT 