#!/usr/bin/env python3
"""
Скрипт для разделения 24-словного мнемоника на 3 шарда по 8 слов
"""

import sys

def split_mnemonic(mnemonic: str):
    """
    Разделяет 24-словный мнемоник на 3 шарда по 8 слов
    """
    words = mnemonic.split()
    
    if len(words) != 24:
        print(f"Ошибка: Мнемоник должен содержать 24 слова, получено {len(words)}")
        sys.exit(1)
    
    shard1 = ' '.join(words[0:8])
    shard2 = ' '.join(words[8:16])
    shard3 = ' '.join(words[16:24])
    
    return shard1, shard2, shard3


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python split_mnemonic.py '<24-word mnemonic>'")
        print("\nПример:")
        print("  python split_mnemonic.py 'abandon abandon abandon ... about'")
        sys.exit(1)
    
    mnemonic = sys.argv[1]
    
    shard1, shard2, shard3 = split_mnemonic(mnemonic)
    
    print("\n=== МНЕМОНИК РАЗДЕЛЕН НА 3 ШАРДА (3 из 3) ===\n")
    print("Каждая нода хранит ТОЛЬКО СВОЙ шард (8 слов).")
    print("Для генерации кошелька/подписи нужны ВСЕ 3 ноды.\n")
    
    print("Node 1 (слова 1-8):")
    print(f"  {shard1}\n")
    
    print("Node 2 (слова 9-16):")
    print(f"  {shard2}\n")
    
    print("Node 3 (слова 17-24):")
    print(f"  {shard3}\n")
    
    print("Добавьте в .env файл:\n")
    print(f"MPC_NODE_1_SHARD=\"{shard1}\"")
    print(f"MPC_NODE_2_SHARD=\"{shard2}\"")
    print(f"MPC_NODE_3_SHARD=\"{shard3}\"")
    print()
