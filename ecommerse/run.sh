#!/bin/bash
brew services start redis
source ../.venv/bin/activate

# Start celery in background
celery -A ecommerse worker --loglevel=info &

# Start django
python manage.py runserver