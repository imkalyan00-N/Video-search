# Use official Python lightweight image
FROM python:3.10-slim

# Install FFmpeg for video processing
RUN apt-get update && apt-get install -y ffmpeg

# Set working directory
WORKDIR /app

# Copy files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

# Expose port and run the app
EXPOSE 10000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]
