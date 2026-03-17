FROM python:3.11-slim

WORKDIR /app

# Install git, nodejs, npm, and build dependencies for python packages
RUN apt-get update && apt-get install -y git curl build-essential libpq-dev python3-dev && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
