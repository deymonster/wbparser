#!/bin/bash

set -e

# Apply Alembic migrations
alembic upgrade head
# Apply initial data
python3 initial_data.py
# Start Bot
python3 main_bot.py