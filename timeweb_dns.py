#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
timeweb_dns.py — управление DNS-записями домена в Timeweb Cloud через API.

Использует токен API (панель Timeweb Cloud → Настройки → API → создать токен).
Токен передаётся через переменную окружения TW_TOKEN (или --token).

Поддерживает:
  list                        — показать DNS-записи домена
  add-txt DOMAIN HOST VALUE   — добавить TXT-запись
  del-host DOMAIN HOST        — удалить записи с указанным host (осторожно!)
  acme-helper                 — режим для ручного DNS-01 certbot (выводит host/value)

Пример:
  export TW_TOKEN='твой_токен'
  python3 timeweb_dns.py list --domain 24ecolife.ru
  python3 timeweb_dns.py add-txt 24ecolife.ru _acme-challenge "ТОКЕН_ОТ_CERTBOT"
  python3 timeweb_dns.py add-txt 24ecolife.ru _acme-challenge.www "ТОКЕН_ОТ_CERTBOT"
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = "https://api.timeweb.cloud/api/v1"


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _req(method, path, token, body=None):
    url = API_BASE + path
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(token), method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return resp.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        return e.code, raw
    except Exception as e:  # noqa: BLE001
        return -1, str(e)


def list_records(domain, token):
    code, raw = _req("GET", f"/domains/{domain}/dns-records", token)
    if code != 200:
        print(f"[ERROR] GET DNS-records: HTTP {code}\n{raw}", file=sys.stderr)
        return None
    try:
        return json.loads(raw)
    except Exception:
        print(f"[ERROR] Не удалось разобрать ответ: {raw}", file=sys.stderr)
        return None


def add_txt(domain, host, value, token, ttl=300):
    # Тело по схеме Timeweb Cloud: record { type, host, value, ttl }
    body = {
        "record": {
            "type": "TXT",
            "host": host,
            "value": value,
            "ttl": ttl,
        }
    }
    code, raw = _req("POST", f"/domains/{domain}/dns-records", token, body)
    if code in (200, 201):
        print(f"[OK] TXT добавлен: {host} = {value}")
        return True
    else:
        print(f"[ERROR] POST DNS-record: HTTP {code}\n{raw}", file=sys.stderr)
        # Fallback: попробуем плоскую схему без вложенного record
        body2 = {"type": "TXT", "host": host, "value": value, "ttl": ttl}
        code, raw = _req("POST", f"/domains/{domain}/dns-records", token, body2)
        if code in (200, 201):
            print(f"[OK] TXT добавлен (плоская схема): {host} = {value}")
            return True
        print(f"[ERROR] Fallback тоже не сработал: HTTP {code}\n{raw}", file=sys.stderr)
        return False


def del_by_host(domain, host, token):
    """Удаляет DNS-записи, у которых поле 'host' равно указанному."""
    data = list_records(domain, token)
    if not data:
        return
    # Формат ответа Timeweb: {"dns_records": [ ... ]} или {"records": [...]}
    records = data.get("dns_records") or data.get("records") or []
    removed = 0
    for r in records:
        # Определяем имя хоста из записи
        r_host = r.get("host") or r.get("name") or r.get("fqdn") or ""
        rid = r.get("id")
        if rid and r_host.rstrip(".") == host.rstrip("."):
            code, raw = _req("DELETE", f"/domains/{domain}/dns-records/{rid}", token)
            if code in (200, 202, 204):
                print(f"[OK] Удалена запись id={rid}")
                removed += 1
            else:
                print(f"[ERROR] Не удалил id={rid}: HTTP {code}\n{raw}", file=sys.stderr)
    print(f"Удалено записей: {removed}")


def print_friendly(data):
    records = data.get("dns_records") or data.get("records") or []
    if not records:
        print("(записей нет)")
        return
    for r in records:
        print({
            "id": r.get("id"),
            "type": r.get("type"),
            "host": r.get("host") or r.get("name") or r.get("fqdn"),
            "value": r.get("value") or r.get("content") or r.get("target"),
            "ttl": r.get("ttl"),
        })


def main(argv=None):
    p = argparse.ArgumentParser(description="Timeweb Cloud DNS helper")
    p.add_argument("command", choices=["list", "add-txt", "del-host"])
    p.add_argument("--domain", required=True, help="домен (например 24ecolife.ru)")
    p.add_argument("--token", default=os.getenv("TW_TOKEN", ""),
                   help="API-токен или env TW_TOKEN")
    p.add_argument("host", nargs="?", default="")
    p.add_argument("value", nargs="?", default="")
    args = p.parse_args(argv)

    token = args.token.strip()
    if not token:
        print("[ERROR] Не задан токен (TW_TOKEN или --token).", file=sys.stderr)
        return 2

    if args.command == "list":
        data = list_records(args.domain, token)
        if data is not None:
            print_friendly(data)
        return 0

    if args.command == "add-txt":
        if not args.host or not args.value:
            print("[ERROR] Нужны HOST и VALUE.", file=sys.stderr)
            return 2
        return 0 if add_txt(args.domain, args.host, args.value, token) else 1

    if args.command == "del-host":
        if not args.host:
            print("[ERROR] Нужен HOST.", file=sys.stderr)
            return 2
        del_by_host(args.domain, args.host, token)
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())