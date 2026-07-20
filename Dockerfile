FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies for PostGIS, Pillow, and PG driver
RUN apt-get update && apt-get install -y --no-install-recommends \
    binutils \
    gdal-bin \
    libgdal-dev \
    libproj-dev \
    postgresql-client \
    gcc \
    python3-dev \
    musl-dev \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . /app/

# Expose port
EXPOSE 8000

# Default entrypoint runs django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
