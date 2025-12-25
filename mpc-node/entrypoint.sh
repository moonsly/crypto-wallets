#!/bin/bash

# Установка пароля для SSH из переменной окружения
if [ -n "$SSH_PASSWORD" ]; then
    echo "mpcadmin:$SSH_PASSWORD" | chpasswd
    echo "SSH password configured for node $NODE_ID"
else
    echo "WARNING: SSH_PASSWORD not set for node $NODE_ID"
    echo "mpcadmin:changeme" | chpasswd
fi

# Запуск SSH сервера
/usr/sbin/sshd

echo "Starting MPC Node $NODE_ID"
echo "  - Flask API: port $NODE_PORT"
echo "  - SSH: port 22 (user: mpcadmin)"

# Запуск Flask приложения
exec python app.py
