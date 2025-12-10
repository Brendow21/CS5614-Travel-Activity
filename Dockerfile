FROM python:3.11-slim

# Set working directory to folder containing manage.py
WORKDIR /app/travel_activity

# Copy all project files into container
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt
RUN pip install --no-cache-dir Pillow

# Expose Django port
EXPOSE 8000

# Environment variables
ENV PYTHONPATH=/app/travel_activity
ENV DJANGO_SETTINGS_MODULE=travel_activity.settings
ENV DJANGO_AUTORELOAD=0
ENV PYTHONUNBUFFERED=1

# Run Gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:8000", "travel_activity.wsgi:application"]
