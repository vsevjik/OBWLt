#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import urllib.request
import re
from datetime import datetime

print("="*60)
print("🚀 МИНИМАЛЬНАЯ ТЕСТОВАЯ ВЕРСИЯ")
print("="*60)

print(f"🐍 Python: {sys.version}")
print(f"📂 Директория: {os.getcwd()}")
print(f"📁 Права на запись: {os.access('.', os.W_OK)}")
print(f"📄 Файлы: {os.listdir('.')}")

# Создаём тестовый sources.txt если нет
if not os.path.exists('sources.txt'):
    print("📝 Создаю sources.txt")
    with open('sources.txt', 'w') as f:
        f.write("https://raw.githubusercontent.com/igareck/vpn-configs-for-russia/main/BLACK_VLESS_RUS.txt\n")
    print("✅ sources.txt создан")

# Читаем sources.txt
print("\n📖 Читаю sources.txt:")
with open('sources.txt', 'r') as f:
    urls = [line.strip() for line in f if line.strip()]
    for url in urls:
        print(f"   • {url}")

# Пробуем скачать
print("\n📥 Пробую скачать...")
VLESS_REGEX = re.compile(r"vless://[^\s]+", re.IGNORECASE)
all_configs = []

for url in urls:
    print(f"   Загрузка: {url[:50]}...")
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode('utf-8')
            found = VLESS_REGEX.findall(content)
            all_configs.extend(found)
            print(f"   ✅ Найдено: {len(found)} конфигов")
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")

print(f"\n📊 Всего конфигов: {len(all_configs)}")

# Сохраняем в файл
output_file = "url_work.txt"
print(f"\n💾 Сохраняю в {output_file}...")
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        for cfg in all_configs[:100]:  # первые 100 для теста
            f.write(cfg + '\n')
    print(f"✅ Файл {output_file} создан")
    print(f"📏 Размер файла: {os.path.getsize(output_file)} байт")
    print(f"📄 Содержимое (первые 5 строк):")
    with open(output_file, 'r') as f:
        for i, line in enumerate(f):
            if i < 5:
                print(f"   {i+1}. {line[:80]}...")
            else:
                break
except Exception as e:
    print(f"❌ Ошибка при сохранении: {e}")

print("\n📁 Финальный список файлов:")
for f in os.listdir('.'):
    if os.path.isfile(f):
        size = os.path.getsize(f)
        print(f"   • {f} ({size} байт)")

print("\n" + "="*60)
print("✅ ТЕСТ ЗАВЕРШЁН")
print("="*60)
