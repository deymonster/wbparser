#!/bin/bash

set -e

# Apply Alembic migrations
alembic upgrade head
# Start Bot
python3 main_bot.py