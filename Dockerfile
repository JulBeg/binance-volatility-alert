# Use an official lightweight Python image
FROM python:3.9-slim

# Install required dependencies
RUN pip install requests

# Set working directory
WORKDIR /app

# Copy Python script into the container
COPY binance_alert.py .

# Run the script
CMD ["python", "binance_alert.py"]
