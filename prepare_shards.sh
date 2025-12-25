#!/bin/bash

# Скрипт для автоматического разделения MASTER_SEED на 3 шарда
# Запускается перед docker-compose up

if [ ! -f .env ]; then
    echo "Ошибка: .env файл не найден"
    echo "Скопируйте .env.example в .env и заполните MASTER_SEED"
    exit 1
fi

# Загружаем MASTER_SEED из .env
source .env

if [ -z "$MASTER_SEED" ]; then
    echo "Ошибка: MASTER_SEED не задан в .env"
    exit 1
fi

# Разделяем на массив слов
words=($MASTER_SEED)

if [ ${#words[@]} -ne 24 ]; then
    echo "Ошибка: MASTER_SEED должен содержать 24 слова, получено ${#words[@]}"
    exit 1
fi

# Делим на 3 шарда по 8 слов
SHARD1="${words[@]:0:8}"
SHARD2="${words[@]:8:8}"
SHARD3="${words[@]:16:8}"

# Добавляем/обновляем шарды в .env
if grep -q "MPC_NODE_1_SHARD=" .env; then
    sed -i "s|^MPC_NODE_1_SHARD=.*|MPC_NODE_1_SHARD=\"$SHARD1\"|" .env
    sed -i "s|^MPC_NODE_2_SHARD=.*|MPC_NODE_2_SHARD=\"$SHARD2\"|" .env
    sed -i "s|^MPC_NODE_3_SHARD=.*|MPC_NODE_3_SHARD=\"$SHARD3\"|" .env
else
    echo "" >> .env
    echo "# Автоматически сгенерированные шарды (не редактировать вручную)" >> .env
    echo "MPC_NODE_1_SHARD=\"$SHARD1\"" >> .env
    echo "MPC_NODE_2_SHARD=\"$SHARD2\"" >> .env
    echo "MPC_NODE_3_SHARD=\"$SHARD3\"" >> .env
fi

echo "✓ Мнемоник разделен на 3 шарда:"
echo "  Node 1: $SHARD1"
echo "  Node 2: $SHARD2"
echo "  Node 3: $SHARD3"
echo ""
echo "Шарды добавлены в .env файл"
