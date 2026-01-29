# Contributing to Twitter Monitor

First off, thank you for considering contributing to Twitter Monitor! It's people like you that make this tool better for everyone.

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the existing issues to avoid duplicates. When you create a bug report, include as many details as possible:

**Bug Report Template:**
- **Description**: Clear description of the bug
- **Steps to Reproduce**: How to reproduce the issue
- **Expected Behavior**: What should happen
- **Actual Behavior**: What actually happens
- **Environment**:
  - OS: [e.g., macOS 14.0, Ubuntu 22.04, Windows 11]
  - Python version: [e.g., 3.10.5]
  - LangGraph version: [e.g., 0.2.0]
- **Logs**: Relevant error messages or logs

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:

- **Use case**: Why is this enhancement useful?
- **Describe the solution**: How should it work?
- **Describe alternatives**: What other solutions have you considered?
- **Additional context**: Screenshots, mockups, etc.

### Pull Requests

1. **Fork the repo** and create your branch from `main`
2. **Make your changes**:
   - Follow the existing code style
   - Update documentation if needed
   - Add tests if applicable
3. **Test your changes**:
   ```bash
   # Test login
   ./login.sh
   ./check_login.sh

   # Test the workflow
   python3 test_login_detection.py
   python3 graph.py
   ```
4. **Commit your changes**:
   - Use clear commit messages
   - Reference issues if applicable (e.g., "Fix #123")
5. **Push to your fork** and submit a pull request

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/twitter-monitor.git
cd twitter-monitor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
npm install -g @browserbase/agent-browser

# Configure
cp .env.example .env
# Edit .env with your credentials

# Login to Twitter
./login.sh

# Test
python3 test_login_detection.py
```

## Code Style

### Python

- Follow [PEP 8](https://peps.python.org/pep-0008/)
- Use meaningful variable and function names
- Add docstrings to classes and functions
- Keep functions focused and small

**Example:**
```python
def _extract_tweets(self, snapshot: dict) -> List[Dict[str, Any]]:
    """
    Extract tweets from browser snapshot

    Args:
        snapshot: Browser snapshot from agent-browser

    Returns:
        List of tweet dictionaries with content, author, etc.
    """
    # Implementation
```

### Shell Scripts

- Use `#!/bin/bash` shebang
- Add comments for non-obvious operations
- Use `set -e` to exit on errors
- Quote variables to handle spaces

## Project Structure

```
twitter-monitor/
├── graph.py              # Main workflow
├── agents/
│   ├── base.py          # Base agent class
│   ├── llm_factory.py   # LLM provider factory
│   ├── fetch_agent/     # Tweet fetching
│   ├── analyse_agent/   # AI analysis
│   └── push_agent/      # Telegram push
├── login.sh             # Login script
├── run.sh               # Cron script
└── tests/               # Tests (future)
```

## Adding New Features

### Adding a New LLM Provider

1. Add configuration in `agents/llm_factory.py`:
   ```python
   "newprovider": {
       "base_url_env": "NEWPROVIDER_BASE_URL",
       "api_key_env": "NEWPROVIDER_API_KEY",
       "model_env": "NEWPROVIDER_MODEL",
       "defaults": {...}
   }
   ```

2. Add to `.env.example`:
   ```bash
   # --- New Provider ---
   NEWPROVIDER_BASE_URL=https://api.example.com/v1
   NEWPROVIDER_API_KEY=your_key
   NEWPROVIDER_MODEL=model-name
   ```

3. Update documentation in README.md

### Adding a New Node to LangGraph

1. Implement the node function in `graph.py`:
   ```python
   def _new_node(self, state: MonitorState) -> dict:
       """Your node implementation"""
       # Process state
       return {"new_field": value}
   ```

2. Add node to the graph:
   ```python
   builder.add_node("new_node", self._new_node)
   builder.add_edge("previous_node", "new_node")
   ```

3. Update `MonitorState` TypedDict if adding new fields

## Testing

Currently, testing is manual. Automated tests are welcome contributions!

**Manual Testing Checklist:**
- [ ] Login flow works (`./login.sh`)
- [ ] Login verification works (`./check_login.sh`)
- [ ] Tweet fetching works
- [ ] AI analysis produces valid output
- [ ] Telegram push succeeds
- [ ] No errors in logs

## Documentation

- Update README.md for user-facing changes
- Update docstrings for code changes
- Add comments for complex logic
- Update CHANGELOG.md for releases

## Questions?

Feel free to open an issue with your question or reach out to the maintainers.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
