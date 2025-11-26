# Dockerfile.worker
FROM python:3.11-slim

# System deps needed to build nsjail
RUN apt-get update && apt-get install -y \
    git build-essential pkg-config \
    libprotobuf-dev protobuf-compiler \
    libnl-route-3-dev libcap-dev libseccomp-dev \
    flex bison \
    ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Install nsjail from source
RUN git clone https://github.com/google/nsjail.git /opt/nsjail && \
    cd /opt/nsjail && make && \
    cp nsjail /usr/bin/nsjail && \
    rm -rf /opt/nsjail

WORKDIR /app

# Copy dependency file first to leverage Docker caching
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY worker_app.py /app/worker_app.py
COPY runner.py     /app/runner.py

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "worker_app:app"]
