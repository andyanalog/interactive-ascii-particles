# Use a multi-stage build to install Node.js and then Python dependencies
FROM node:14 AS builder

# Copy the React code into the container at this path
COPY package*.json ./

# Install dependencies from the package file
RUN npm install

# Build the React app (using Webpack or another bundler)
RUN npm run build

# Use a separate stage to install Python dependencies
FROM python:3.12-slim AS python-builder

RUN pip install --no-cache-dir opencv-python

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
    
#

# Copy the requirements.txt into this new image
COPY requirements.txt .

# Install required libraries
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's files (Flask code)
COPY . .

# Expose port 80 to be accessible from outside the container
EXPOSE 5000

# Step 10: Run Gunicorn when the container launches
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]