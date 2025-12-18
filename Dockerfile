# Use an official Python runtime as a parent image
FROM python:3.11-slim

# 1. Install Tesseract and system dependencies
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# 2. Set the working directory
WORKDIR /app

# 3. Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy the rest of your app
COPY . .

# 5. Start the application
# Render uses the $PORT environment variable automatically
CMD ["sh", "-c", "uvicorn api.index:app --host 0.0.0.0 --port ${PORT:-8000}"]