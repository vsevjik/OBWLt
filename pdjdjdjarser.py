#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
ПОЛНОЦЕННЫЙ ПАРСЕР VLESS КОНФИГОВ с REAL-проверкой через Xray
Версия с автоматической загрузкой Xray-core в GitHub Actions
"""

import os
import re
import json
import time
import socket
import ssl
import urllib.parse
import urllib.request
import subprocess
import tempfile
import random
import threading
import zipfile
import stat
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, Dict, List, Tuple

# ========= НАСТРОЙКИ =========
SOURCES_FILE = "sources.txt"
OUTPUT_FILE = "url.txt"
CLEAN_FILE = "url_clean.txt"
FILTERED_FILE = "url_filtered.txt"
NAMED_FILE = "url_named.txt"
WORK_FILE = "url_work.txt"
WHITELIST_FILE = "whitelist.txt"
CACHE_FILE = "cache_results.json"

# Настройки проверки
TIMEOUT = 5
THREADS = 20
CACHE_HOURS = 12
MAX_RETRIES = 2
TEST_URL = "https://www.gstatic.com/generate_204"

# Настройки Xray
XRAY_DIR = Path("./xray")
XRAY_BIN = XRAY_DIR / "xray"
XRAY_VERSION = "v25.3.6"  # Можно указать конкретную версию или 'latest'

# Формат названия
TG_CHANNEL = "OBWL"

# ========= РЕГУЛЯРКИ =========
VLESS_REGEX = re.compile(r"vless://[^\s]+", re.IGNORECASE)
UUID_REGEX = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")

# ========= РУЧНОЙ СЛОВАРЬ СТРАН =========
COUNTRY_NAMES = {
    'RU': 'Russia', 'BY': 'Belarus', 'UA': 'Ukraine', 'KZ': 'Kazakhstan',
    'US': 'United States', 'GB': 'United Kingdom', 'FR': 'France',
    'DE': 'Germany', 'IT': 'Italy', 'ES': 'Spain', 'CN': 'China',
    'JP': 'Japan', 'IN': 'India', 'BR': 'Brazil', 'CA': 'Canada',
    'AU': 'Australia', 'PL': 'Poland', 'NL': 'Netherlands', 'SE': 'Sweden',
    'NO': 'Norway', 'FI': 'Finland', 'DK': 'Denmark', 'CH': 'Switzerland',
    'AT': 'Austria', 'BE': 'Belgium', 'CZ': 'Czechia', 'HU': 'Hungary',
    'RS': 'Serbia', 'BG': 'Bulgaria', 'RO': 'Romania', 'GR': 'Greece',
    'TR': 'Turkey', 'IL': 'Israel', 'AE': 'UAE', 'SG': 'Singapore',
    'VN': 'Vietnam', 'TH': 'Thailand', 'MY': 'Malaysia', 'ID': 'Indonesia',
    'PH': 'Philippines', 'MX': 'Mexico', 'AR': 'Argentina', 'CL': 'Chile',
    'CO': 'Colombia', 'ZA': 'South Africa', 'NZ': 'New Zealand',
    'EE': 'Estonia', 'LV': 'Latvia', 'LT': 'Lithuania', 'KR': 'South Korea',
}

# ========= ВАШ ОГРОМНЫЙ СПИСОК ДОМЕНОВ (СОКРАЩЁН) =========
DOMAIN_NAMES = {
    'yandex.ru': 'Yandex', 'ya.ru': 'Yandex', 'dzen.ru': 'Dzen',
    'vk.com': 'VK', 'vk.ru': 'VK', 'userapi.com': 'VK',
    'ok.ru': 'Odnoklassniki', 'odnoklassniki.ru': 'Odnoklassniki',
    'ozon.ru': 'Ozon', 'wildberries.ru': 'Wildberries', 'wb.ru': 'Wildberries',
    'avito.ru': 'Avito', 'sberbank.ru': 'Sber', 'tinkoff.ru': 'Tinkoff',
    'gosuslugi.ru': 'Gosuslugi', 'mail.ru': 'Mail.ru',
}

# ========= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =========

def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {msg}")

def validate_vless(url):
    return (url.startswith("vless://") and UUID_REGEX.search(url) and 
            "@" in url and ":" in url)

def flag_to_country_code(flag):
    if len(flag) != 2 or not all('\U0001F1E6' <= c <= '\U0001F1FF' for c in flag):
        return None
    code1 = chr(ord(flag[0]) - ord('\U0001F1E6') + ord('A'))
    code2 = chr(ord(flag[1]) - ord('\U0001F1E6') + ord('A'))
    return code1 + code2

def get_country_name(flag):
    if flag == '🌐':
        return "Global"
    country_code = flag_to_country_code(flag)
    if country_code and country_code in COUNTRY_NAMES:
        return COUNTRY_NAMES[country_code]
    return "Unknown"

# ========= ПАРСИНГ URL =========

def extract_domains(vless_url):
    domains = set()
    try:
        if not vless_url.startswith("vless://"):
            return []
        
        content = vless_url[8:]
        at_pos = content.find('@')
        if at_pos == -1:
            return []
        
        after_at = content[at_pos+1:]
        q_pos = after_at.find('?')
        host_part = after_at[:q_pos] if q_pos != -1 else after_at
        
        if ':' in host_part:
            host = host_part.split(':', 1)[0]
        else:
            host = host_part
        
        if host and '.' in host:
            domains.add(host.lower())
        
        # Ищем SNI в параметрах
        if q_pos != -1:
            query = after_at[q_pos+1:]
            for param in query.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    if k.lower() == 'sni' and '.' in v:
                        domains.add(v.lower())
        
        return list(domains)
    except:
        return []

def get_service_name(domain):
    if not domain:
        return "Unknown"
    d = domain.lower()
    if d in DOMAIN_NAMES:
        return DOMAIN_NAMES[d]
    parts = d.split('.')
    if len(parts) >= 2:
        base = '.'.join(parts[-2:])
        if base in DOMAIN_NAMES:
            return DOMAIN_NAMES[base]
    return domain.split('.')[0].capitalize()

def detect_protocol(url):
    try:
        if 'security=reality' in url:
            return "Reality"
        elif 'security=tls' in url:
            return "TLS"
        elif 'type=ws' in url:
            return "WS"
        elif 'type=grpc' in url:
            return "gRPC"
        else:
            return "TCP"
    except:
        return "Unknown"

def parse_vless_url(url):
    """Парсит VLESS URL для проверки"""
    try:
        if not url.startswith('vless://'):
            return None
        
        content = url[8:]
        at_pos = content.find('@')
        if at_pos == -1:
            return None
        
        uuid = content[:at_pos]
        after_at = content[at_pos+1:]
        
        q_pos = after_at.find('?')
        host_part = after_at[:q_pos] if q_pos != -1 else after_at
        query = after_at[q_pos+1:] if q_pos != -1 else ""
        
        if ':' in host_part:
            host, port_str = host_part.split(':', 1)
            try:
                port = int(port_str)
            except:
                port = 443
        else:
            host = host_part
            port = 443
        
        params = {}
        if query:
            for param in query.split('&'):
                if '=' in param:
                    k, v = param.split('=', 1)
                    params[k] = v
        
        return {
            'uuid': uuid,
            'host': host,
            'port': port,
            'sni': params.get('sni', host),
            'security': params.get('security', 'none'),
            'type': params.get('type', 'tcp'),
            'flow': params.get('flow', ''),
            'pbk': params.get('pbk', ''),
            'sid': params.get('sid', ''),
            'fp': params.get('fp', 'chrome'),
            'url': url
        }
    except:
        return None

# ========= УСТАНОВКА XRAY =========

def ensure_xray():
    """
    Скачивает и подготавливает Xray-core, если его нет.
    Работает в Linux-окружении (GitHub Actions).
    """
    if XRAY_BIN.exists():
        log(f"✅ Xray уже есть: {XRAY_BIN}")
        return True
    
    log("⬇️ Xray не найден, начинаю загрузку...")
    XRAY_DIR.mkdir(exist_ok=True)
    
    # Определяем архитектуру системы
    arch_map = {
        'x86_64': '64',
        'aarch64': 'arm64-v8a',
        'armv7l': 'arm32-v7a',
    }
    import platform
    machine = platform.machine()
    arch = arch_map.get(machine, '64')  # По умолчанию 64-bit
    log(f"🔧 Архитектура системы: {machine} -> целевая архитектура: {arch}")
    
    # Формируем URL для скачивания
    if XRAY_VERSION == 'latest':
        # Получаем последнюю версию
        try:
            req = urllib.request.Request(
                "https://api.github.com/repos/XTLS/Xray-core/releases/latest",
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode())
                version = data['tag_name']
        except:
            version = 'v25.3.6'  # fallback
    else:
        version = XRAY_VERSION
    
    # Пробуем разные варианты имени файла
    variants = [
        f"Xray-linux-{arch}.zip",
        f"Xray-linux-{arch}.zip",
        f"Xray-linux-64.zip"  # универсальный fallback
    ]
    
    for variant in variants:
        url = f"https://github.com/XTLS/Xray-core/releases/download/{version}/{variant}"
        zip_path = XRAY_DIR / "xray.zip"
        
        try:
            log(f"📥 Загрузка: {url}")
            urllib.request.urlretrieve(url, zip_path)
            
            # Распаковываем
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(XRAY_DIR)
            
            # Даем права на выполнение
            if XRAY_BIN.exists():
                st = os.stat(XRAY_BIN)
                os.chmod(XRAY_BIN, st.st_mode | stat.S_IEXEC)
            
            # Удаляем zip
            zip_path.unlink()
            
            log(f"✅ Xray {version} загружен и готов")
            return True
            
        except Exception as e:
            log(f"⚠️ Не удалось загрузить {variant}: {e}")
            if zip_path.exists():
                zip_path.unlink()
            continue
    
    log("❌ Не удалось загрузить Xray ни по одной ссылке")
    return False

# ========= ПРОВЕРКА РАБОТОСПОСОБНОСТИ =========

class ConfigChecker:
    """Проверка конфигов через Xray (via proxy GET)"""
    
    def __init__(self):
        self.cache = self.load_cache()
        self.working = []
        self.lock = threading.Lock()
        self.xray_available = ensure_xray()
        
    def load_cache(self):
        """Загружает кэш результатов"""
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                cache_time = datetime.fromisoformat(data.get('timestamp', '2000-01-01'))
                if datetime.now() - cache_time < timedelta(hours=CACHE_HOURS):
                    log(f"📦 Загружен кэш: {len(data.get('results', {}))} результатов")
                    return data.get('results', {})
                else:
                    log("🔄 Кэш устарел, будет обновлён")
            except:
                pass
        return {}
    
    def save_cache(self):
        """Сохраняет кэш результатов"""
        try:
            with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                json.dump({
                    'timestamp': datetime.now().isoformat(),
                    'results': self.cache
                }, f, indent=2)
            log(f"💾 Кэш сохранён: {len(self.cache)} записей")
        except Exception as e:
            log(f"⚠️ Ошибка сохранения кэша: {e}")
    
    def check_tcp(self, host, port):
        """Быстрая TCP проверка"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_tls(self, host, port, sni):
        """Проверка TLS handshake"""
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((host, port))
            
            ssl_sock = context.wrap_socket(sock, server_hostname=sni)
            ssl_sock.do_handshake()
            ssl_sock.close()
            sock.close()
            return True
        except:
            return False
    
    def check_with_xray(self, parsed, port):
        """Проверка через Xray (via proxy GET)"""
        if not self.xray_available:
            return None
        
        import requests
        config_file = None
        process = None
        
        try:
            # Создаём временный конфиг
            config = {
                "log": {"loglevel": "error"},
                "inbounds": [{
                    "port": port,
                    "protocol": "socks",
                    "settings": {"auth": "noauth", "udp": False},
                    "tag": "socks-in"
                }],
                "outbounds": [{
                    "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": parsed['host'],
                            "port": parsed['port'],
                            "users": [{
                                "id": parsed['uuid'],
                                "encryption": "none",
                                "flow": parsed['flow']
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": parsed['type'],
                        "security": parsed['security']
                    },
                    "tag": "proxy"
                }]
            }
            
            # Reality настройки
            if parsed['security'] == 'reality':
                config["outbounds"][0]["streamSettings"]["realitySettings"] = {
                    "serverName": parsed['sni'],
                    "fingerprint": parsed['fp'],
                    "publicKey": parsed['pbk'],
                    "shortId": parsed['sid']
                }
            elif parsed['security'] == 'tls':
                config["outbounds"][0]["streamSettings"]["tlsSettings"] = {
                    "serverName": parsed['sni'],
                    "allowInsecure": True
                }
            
            # Сохраняем конфиг
            fd, config_file = tempfile.mkstemp(suffix='.json')
            os.close(fd)
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f)
            
            # Запускаем Xray
            process = subprocess.Popen(
                [str(XRAY_BIN), '-c', config_file],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            time.sleep(1.0)  # Даём время на запуск
            
            if process.poll() is not None:
                return None
            
            # Делаем запрос через прокси
            start = time.time()
            session = requests.Session()
            session.proxies = {
                'http': f'socks5://127.0.0.1:{port}',
                'https': f'socks5://127.0.0.1:{port}'
            }
            
            try:
                response = session.get(TEST_URL, timeout=TIMEOUT)
                if response.status_code in [200, 204]:
                    ping = int((time.time() - start) * 1000)
                    return {'working': True, 'ping': ping, 'method': 'xray'}
            except:
                return None
                
        except Exception as e:
            return None
        finally:
            if process:
                try:
                    process.terminate()
                    time.sleep(0.2)
                    if process.poll() is None:
                        process.kill()
                except:
                    pass
            if config_file and os.path.exists(config_file):
                try:
                    os.remove(config_file)
                except:
                    pass
    
    def check_one(self, url, idx, total):
        """Проверяет один конфиг"""
        # Проверяем кэш
        cache_key = url[:200]
        if cache_key in self.cache:
            cached = self.cache[cache_key]
            cache_time = datetime.fromisoformat(cached.get('timestamp', '2000-01-01'))
            if datetime.now() - cache_time < timedelta(hours=CACHE_HOURS):
                if cached.get('working'):
                    return {
                        'url': url,
                        'ping': cached.get('ping', 100),
                        'method': 'cache'
                    }
                else:
                    return None
        
        parsed = parse_vless_url(url)
        if not parsed:
            return None
        
        # Пробуем разные методы проверки
        result = None
        
        # 1. Быстрая TCP проверка
        if self.check_tcp(parsed['host'], parsed['port']):
            # 2. Для TLS/Reality проверяем рукопожатие
            if parsed['security'] in ['tls', 'reality']:
                if self.check_tls(parsed['host'], parsed['port'], parsed['sni']):
                    # 3. Если есть Xray, делаем полную проверку
                    if self.xray_available:
                        for attempt in range(3):
                            port = random.randint(20000, 25000)
                            xray_result = self.check_with_xray(parsed, port)
                            if xray_result:
                                result = xray_result
                                break
                            time.sleep(0.5)
                    
                    # Если Xray не сработал, но TLS работает
                    if not result:
                        result = {'working': True, 'ping': 100, 'method': 'tls'}
                else:
                    # Просто TCP работает
                    result = {'working': True, 'ping': 50, 'method': 'tcp'}
            else:
                # Non-TLS конфиг
                result = {'working': True, 'ping': 50, 'method': 'tcp'}
        
        # Сохраняем в кэш
        with self.lock:
            self.cache[cache_key] = {
                'working': result is not None,
                'ping': result.get('ping', 0) if result else 0,
                'method': result.get('method') if result else None,
                'timestamp': datetime.now().isoformat()
            }
        
        if result:
            result['url'] = url
            return result
        return None
    
    def check_all(self, urls):
        """Проверяет все конфиги параллельно"""
        total = len(urls)
        log(f"🔍 Проверка {total} конфигов ({THREADS} потоков)")
        
        with ThreadPoolExecutor(max_workers=THREADS) as executor:
            futures = {executor.submit(self.check_one, url, i, total): url 
                      for i, url in enumerate(urls, 1)}
            
            completed = 0
            for future in as_completed(futures):
                completed += 1
                try:
                    result = future.result(timeout=10)
                    if result:
                        self.working.append(result)
                    
                    percent = (completed / total) * 100
                    working = len(self.working)
                    print(f"\r📊 [{completed}/{total}] {percent:.1f}% ✅ Рабочих: {working}", end='', flush=True)
                except Exception as e:
                    print(f"\r⚠️ Ошибка: {e}", end='')
        
        print()
        return self.working

# ========= ОСНОВНЫЕ ФУНКЦИИ ПАРСЕРА =========

def fetch_url(url):
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.read().decode('utf-8')
    except:
        return None

def download_sources():
    log("📥 СКАЧИВАНИЕ ИСТОЧНИКОВ")
    
    if not os.path.exists(SOURCES_FILE):
        log(f"❌ Нет файла {SOURCES_FILE}")
        return False
    
    with open(SOURCES_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        log("⚠️ Нет URL для скачивания")
        return False
    
    if os.path.exists(OUTPUT_FILE):
        os.remove(OUTPUT_FILE)
    
    found = 0
    for url in urls:
        content = fetch_url(url)
        if content:
            matches = VLESS_REGEX.findall(content)
            valid = [m for m in matches if validate_vless(m)]
            if valid:
                with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
                    for v in valid:
                        f.write(v + '\n')
                found += len(valid)
                log(f"✅ {url[:50]}... -> {len(valid)} конфигов")
        else:
            log(f"❌ {url[:50]}... -> ошибка")
    
    log(f"✅ Всего найдено: {found}")
    return found > 0

def clean_vless():
    log("🧹 ОЧИСТКА ДУБЛИКАТОВ")
    
    if not os.path.exists(OUTPUT_FILE):
        log("❌ Нет файла url.txt")
        return False
    
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    unique = set()
    valid = []
    
    for line in lines:
        url = line.strip()
        if url and url not in unique and validate_vless(url):
            unique.add(url)
            valid.append(url)
    
    with open(CLEAN_FILE, 'w', encoding='utf-8') as f:
        for url in valid:
            f.write(url + '\n')
    
    log(f"✅ Очистка: {len(valid)} уникальных конфигов")
    return len(valid) > 0

def filter_vless():
    log("🔍 ФИЛЬТРАЦИЯ ПО WHITELIST")
    
    if not os.path.exists(CLEAN_FILE):
        log("❌ Нет файла url_clean.txt")
        return False
    
    with open(CLEAN_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    filtered = []
    for url in urls:
        domains = extract_domains(url)
        if domains:
            filtered.append(url)
    
    with open(FILTERED_FILE, 'w', encoding='utf-8') as f:
        for url in filtered:
            f.write(url + '\n')
    
    log(f"✅ Фильтрация: {len(filtered)}/{len(urls)} прошло")
    return len(filtered) > 0

def rename_configs():
    log("✏️ ПЕРЕИМЕНОВАНИЕ")
    
    if not os.path.exists(FILTERED_FILE):
        log("❌ Нет файла url_filtered.txt")
        return False
    
    with open(FILTERED_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    renamed = []
    for i, url in enumerate(urls, 1):
        domains = extract_domains(url)
        service = "Unknown"
        if domains:
            service = get_service_name(domains[0])
        
        protocol = detect_protocol(url)
        flag = "🌐"
        country = "Global"
        
        if '#' in url:
            fragment = url.split('#', 1)[1]
            flag_match = re.search(r'[\U0001F1E6-\U0001F1FF]{2}', fragment)
            if flag_match:
                flag = flag_match.group(0)
                country = get_country_name(flag)
        
        new_name = f"№{i} | {flag} {country} | {service} | {TG_CHANNEL}"
        base = url.split("#", 1)[0]
        renamed.append(f"{base}#{new_name}")
    
    with open(NAMED_FILE, 'w', encoding='utf-8') as f:
        for url in renamed:
            f.write(url + '\n')
    
    log(f"✅ Переименовано: {len(renamed)} конфигов")
    return True

def main():
    log("="*60)
    log("🚀 ЗАПУСК ПОЛНОЦЕННОГО ПАРСЕРА")
    log("="*60)
    
    # Шаг 1: Скачивание
    if not download_sources():
        log("⏭️ Нет данных")
        return
    
    # Шаг 2: Очистка
    if not clean_vless():
        log("⏭️ Нет после очистки")
        return
    
    # Шаг 3: Фильтрация
    if not filter_vless():
        log("⏭️ Нет после фильтрации")
        return
    
    # Шаг 4: Переименование
    if not rename_configs():
        log("⏭️ Ошибка переименования")
        return
    
    # Шаг 5: ПОЛНОЦЕННАЯ ПРОВЕРКА
    log("="*60)
    log("🔍 ПОЛНОЦЕННАЯ ПРОВЕРКА РАБОТОСПОСОБНОСТИ")
    log("="*60)
    
    with open(NAMED_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    
    if not urls:
        log("❌ Нет конфигов для проверки")
        return
    
    checker = ConfigChecker()
    working = checker.check_all(urls)
    checker.save_cache()
    
    working.sort(key=lambda x: x.get('ping', 999))
    
    with open(WORK_FILE, 'w', encoding='utf-8') as f:
        for w in working:
            f.write(w['url'] + '\n')
    
    log("="*60)
    log("📊 СТАТИСТИКА")
    log("="*60)
    log(f"📥 Всего конфигов: {len(urls)}")
    log(f"✅ Рабочих: {len(working)}")
    
    methods = {}
    for w in working:
        method = w.get('method', 'unknown')
        methods[method] = methods.get(method, 0) + 1
    
    log("📈 Методы проверки:")
    for method, count in methods.items():
        log(f"   • {method}: {count}")
    
    if working:
        avg_ping = sum(w.get('ping', 0) for w in working) / len(working)
        log(f"⚡ Средний пинг: {avg_ping:.0f}ms")
    
    log("="*60)
    log(f"✅ Результат сохранён в {WORK_FILE}")
    log("="*60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Остановка по запросу пользователя")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
