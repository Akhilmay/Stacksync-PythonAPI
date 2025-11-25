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

RUN ln -s /usr/local/bin/python3 /usr/bin/python3

WORKDIR /app

# Python deps for the worker
RUN pip install --no-cache-dir flask gunicorn

# Copy code
COPY worker_app.py /app/worker_app.py
COPY runner.py     /app/runner.py

EXPOSE 8080

CMD ["gunicorn", "-b", "0.0.0.0:8080", "worker_app:app"]
