FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y wkhtmltopdf

# Set work directory
WORKDIR /app

# Copy project files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Expose port
EXPOSE 8000

# Start the app with Gunicorn
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]