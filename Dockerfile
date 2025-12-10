FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY travel_activity/ ./travel_activity/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=travel_activity.settings

# Collect static files (optional)
# RUN python manage.py collectstatic --noinput

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "travel_activity/manage.py", "runserver", "0.0.0.0:8000"]
