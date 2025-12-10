# Use Python 3.11 slim
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy Django project and src folder
COPY travel_activity/ travel_activity/
COPY src/ src/

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set PYTHONPATH so 'src' can be imported
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Run Django dev server
CMD ["python", "travel_activity/manage.py", "runserver", "0.0.0.0:8000"]
