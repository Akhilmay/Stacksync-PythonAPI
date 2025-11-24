FROM python:3.10-slim

# Install nsjail build dependencies
RUN apt-get update && apt-get install -y \
    git build-essential bison flex pkg-config \
    libprotobuf-dev protobuf-compiler \
    libnl-route-3-dev libcap-dev libseccomp-dev \
    wget ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Build nsjail
RUN git clone https://github.com/google/nsjail.git /tmp/nsjail && \
    cd /tmp/nsjail && make && cp nsjail /usr/bin/nsjail && rm -rf /tmp/nsjail

WORKDIR /app

COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Copy app code
COPY app/ /app/

EXPOSE 8080
ENV PYTHONUNBUFFERED=1

CMD ["gunicorn", "-b", "0.0.0.0:8080", "app:app"]
