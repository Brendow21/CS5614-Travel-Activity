# Use official Python base image
FROM python:3.11-slim

# Set environment vars for Python
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies (required for psycopg2, sqlite, etc)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && apt-get clean

# Copy dependency list first for caching
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire Django project
COPY . /app/

# Expose application port
EXPOSE 8000

# Set working directory to Django project folder that contains manage.py
WORKDIR /app/travel_activity

# Run migrations automatically (optional but recommended)
# Then start Gunicorn
CMD ["gunicorn", "travel_activity.wsgi:application", "--bind", "0.0.0.0:8000"]
