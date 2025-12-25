FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    openssh-server \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Настройка SSH
RUN mkdir -p /var/run/sshd
RUN useradd -m -s /bin/bash mpcadmin && \
    echo "mpcadmin ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

RUN mkdir -p /app/data

ENV PYTHONUNBUFFERED=1

EXPOSE 22

CMD ["./entrypoint.sh"]
