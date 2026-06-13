# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code and databases
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the application using Uvicorn.
# Render/HuggingFace dynamically sets the PORT environment variable,
# so we use shell form to evaluate the $PORT variable with a fallback to 8000.
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
