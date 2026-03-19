# Contributing

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/concrete-sangminlee/weather-slack-bot.git
cd weather-slack-bot
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
make install
pip install pytest
```

## Running Locally

```bash
cp .env.example .env
# Edit .env with your Slack Bot Token and Channel
make run
```

## Running Tests

```bash
make test
```

All tests must pass before submitting a PR.

## Making Changes

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `make test`
5. Commit with a clear message
6. Push and open a Pull Request

## Code Style

- Python 3.12+
- Functions should have docstrings for complex logic
- Korean strings for user-facing Slack messages
- English for code comments and variable names

## Ideas for Contributions

- Add support for more cities/languages
- Add new lifestyle indices
- Improve tip presets for different climates
- Add Slack interactive components (buttons, menus)
- Add webhook support for weather alerts
- Performance optimizations

## Questions?

Open an [issue](https://github.com/concrete-sangminlee/weather-slack-bot/issues) and we'll help you out.
