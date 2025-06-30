FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && \
    apt-get install -y wkhtmltopdf build-essential libssl-dev libffi-dev python3-dev && \
    apt-get clean

# Set work directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN apt-get update && apt-get install -y wkhtmltopdf
# Copy your app code
COPY . .

# Expose port (Render uses 10000 by default, but 8080 is also common)
EXPOSE 10000

# Start the app (adjust if your entrypoint is different)
CMD ["gunicorn", "-b", "0.0.0.0:10000", "app:app"]