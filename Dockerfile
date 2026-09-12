# Use an official Python runtime as a parent image
FROM python:3.11-slim

# 1. Set the working directory
WORKDIR /app

# 2. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. Copy the rest of your app
COPY . .

# 4. Start the application
# Render uses the $PORT environment variable automatically
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]