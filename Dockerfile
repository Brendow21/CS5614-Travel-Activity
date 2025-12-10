FROM python:3.11-slim

# Set working directory to outer travel_activity
WORKDIR /app

# Copy all project files
COPY . /app

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir Pillow

# Expose port
EXPOSE 8000

# Run Gunicorn
ENV PYTHONPATH=/app/src
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "travel_activity.travel_activity.wsgi:application"]

