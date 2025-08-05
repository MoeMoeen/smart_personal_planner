# Scripts Directory

This directory contains all utility scripts for the Smart Personal Planner project.

## Available Scripts

### Bot Launchers
- **`start_telegram_bot.py`** - Main Telegram bot with complex LangGraph agent
- **`simple_telegram_bot.py`** - Alternative simple trust-based Telegram bot

### Database Management
- **`create_db.py`** - Initialize the database schema
- **`reset_db_data.py`** - Reset/clear database data for testing

### System Utilities
- **`preflight_check.py`** - Environment validation and dependency check

## Usage

Run scripts from the project root directory:

```bash
# Start the main bot
python scripts/start_telegram_bot.py

# Start the simple bot
python scripts/simple_telegram_bot.py

# Initialize database
python scripts/create_db.py

# Check environment
python scripts/preflight_check.py
```

**Note**: Ensure your Python environment is activated and all dependencies are installed before running scripts.
