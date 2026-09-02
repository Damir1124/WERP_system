#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-docker-helper.py — «мост» между DSH-агентом и Docker-окружением WERP.

Единая точка входа для рутинных операций с контейнерами. Использует только
стандартную библиотеку (нет внешних зависимостей), поэтому работает и на
Windows-хосте, и внутри любого контейнера с Python 3.

Команды:
    ps                     — список контейнеров со статусом и портами (docker ps -a)
    health                 — статус сервисов docker-compose.yml в виде таблицы
    logs  <container>      — хвост логов контейнера (--tail N, --follow)
    exec  <container> ...  — выполнить команду внутри контейнера
    compose <up|down|stop|restart>  — управление стеком (docker compose)

Флаги:
    --json                 — машиночитаемый вывод (JSON) где возможно
    --debug                — показать сам выполняемый docker-вызов
    -h, --help             — справка

Примеры:
    python dsh-docker-helper.py ps
    python dsh-docker-helper.py health --json
    python dsh-docker-helper.py logs werp_db --tail 100
    python dsh-docker-helper.py exec werp_db pg_isready -U werp_admin -d werp_system
    python dsh-docker-helper.py compose up -d
"""

import argparse
import json
import shutil
import subprocess
import sys

# Сервисы, объявленные в docker-compose.yml проекта WERP.
COMPOSE_SERVICES = [
    "db",
    "redis",
    "web",
    "celery-worker",
    "celery-beat",
    "nginx",
]


def _find_docker():
    """Возвращает путь к docker, либо None если CLI не найден."""
    path = shutil.which("docker")
    if not path:
        print("[ERROR] docker CLI не найден в PATH.", file=sys.stderr)
    return path


def _compose_cmd():
    """docker compose (modern) с fallback на устаревший docker-compose."""
    docker = _find_docker()
    if not docker:
        return None
    # Проверяем, поддерживает ли docker подкоманду compose.
    check = subprocess.run(
        [docker, "compose", "version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if check.returncode == 0:
        return [docker, "compose"]
    old = shutil.which("docker-compose")
    return [old] if old else None


def run(args, check=True, capture=False, debug=False, inherit_env=True):
    """Выполнить команду и вернуть CompletedProcess.

    inherit_env=False — НЕ передавать .env-переменные (избегает утечки секретов
    в stdout при некоторых docker-подкомандах, которые печатают окружение).
    """
    env = None
    if inherit_env is False and sys.platform == "win32":
        # Формируем чистый env: базовые системные пути без пользовательских .env.
        env = {}
        for key in ("PATH", "SystemRoot", "TEMP", "TMP", "ComSpec", "PATHEXT"):
            if key in __import__("os").environ:
                env[key] = __import__("os").environ[key]

    if debug:
        print(f"[debug] $ {' '.join(args)}", file=sys.stderr)

    if capture:
        return subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, env=env,
        )
    return subprocess.run(args, env=env)


def daemon_status():
    """Быстрая проверка доступности демона. Возвращает (bool, str)."""
    docker = _find_docker()
    if not docker:
        return False, "docker CLI отсутствует"
    r = run(
        [docker, "info", "--format", "{{.ServerVersion}}"],
        check=False, capture=True,
    )
    if r.returncode == 0:
        version = r.stdout.strip()
        return True, f"ServerVersion={version}"
    msg = (r.stderr or r.stdout or "").strip().splitlines()
    detail = msg[-1] if msg else "неизвестно"
    return False, detail


def cmd_ps(args):
    docker = _find_docker()
    if not docker:
        return 1
    r = run(
        [docker, "ps", "-a",
         "--format",
         "{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Image}}"],
        check=False, capture=True,
    )
    if r.returncode != 0:
        print((r.stderr or r.stdout or "docker ps failed").rstrip())
        return r.returncode

    rows = []
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < 4:
            parts = (parts + ["", "", "", ""])[:4]
        rows.append({
            "name": parts[0],
            "status": parts[1],
            "ports": parts[2],
            "image": parts[3],
        })

    if args.json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
    else:
        header = f"{'NAME':<28}{'STATUS':<34}{'PORTS':<28}IMAGE"
        print(header)
        for row in rows:
            print(f"{row['name']:<28}{row['status']:<34}{row['ports']:<28}{row['image']}")
    return 0


def cmd_health(args):
    compose = _compose_cmd()
    if not compose:
        print("[ERROR] docker compose недоступен.", file=sys.stderr)
        return 1
    ok, detail = daemon_status()
    if not ok:
        print(f"[ERROR] Docker-демон недоступен: {detail}", file=sys.stderr)
        return 1

    r = run(
        compose + ["ps", "-a", "--format",
                   "{{.Name}}\t{{.Service}}\t{{.Status}}\t{{.Ports}}"],
        check=False, capture=True,
    )
    if r.returncode != 0:
        print((r.stderr or r.stdout or "compose ps failed").rstrip())
        return r.returncode

    live = {}
    for line in r.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        parts = (parts + ["", "", "", ""])[:4]
        live[parts[1]] = {
            "name": parts[0],
            "status": parts[2],
            "ports": parts[3],
        }

    result = []
    for srv in COMPOSE_SERVICES:
        if srv in live:
            result.append({
                "service": srv,
                "state": "up" if "Up" in live[srv]["status"] else
                         ("paused" if "Paused" in live[srv]["status"] else
                          ("exited" if "Exited" in live[srv]["status"] else
                           live[srv]["status"])),
                "raw_status": live[srv]["status"],
                "container": live[srv]["name"],
                "ports": live[srv]["ports"],
            })
        else:
            result.append({
                "service": srv,
                "state": "not_created",
                "raw_status": "—",
                "container": "—",
                "ports": "—",
            })

    if args.json:
        print(json.dumps({"daemon": "up", "services": result},
                         ensure_ascii=False, indent=2))
    else:
        print(f"Demone: UP ({detail})")
        print(f"{'SERVICE':<16}{'STATE':<12}{'CONTAINER':<22}PORTS")
        for s in result:
            print(f"{s['service']:<16}{s['state']:<12}"
                  f"{s['container']:<22}{s['ports']}")
        up = sum(1 for s in result if s["state"] == "up")
        print(f"\nИтого: {up}/{len(result)} сервисов запущены.")
    return 0


def cmd_logs(args):
    docker = _find_docker()
    if not docker:
        return 1
    if not args.container:
        print("[ERROR] Не указан контейнер.", file=sys.stderr)
        return 1
    tail = getattr(args, "tail", "100")
    follow = getattr(args, "follow", False)
    cmd = [docker, "logs", "--tail", str(tail)]
    if follow:
        cmd.append("--follow")
    cmd.append(args.container)
    # При follow выводим потоково (stdout наследуется).
    return run(cmd, check=False).returncode


def cmd_exec(args):
    docker = _find_docker()
    if not docker:
        return 1
    if not args.container:
        print("[ERROR] Не указан контейнер.", file=sys.stderr)
        return 1
    cmd = [docker, "exec"]
    if getattr(args, "it", False):
        cmd += ["-it"]
    cmd += [args.container] + args.command
    return run(cmd, check=False).returncode


def cmd_compose(args):
    compose = _compose_cmd()
    if not compose:
        print("[ERROR] docker compose недоступен.", file=sys.stderr)
        return 1
    action = args.action
    if action not in ("up", "down", "stop", "restart"):
        print(f"[ERROR] Неизвестное действие compose: {action}", file=sys.stderr)
        return 1
    cmd = list(compose) + [action]
    if action == "up":
        cmd.append("-d")   # detached, безопасно не блокирует
    return run(cmd, check=False).returncode


def build_parser():
    # Общие флаги для главной команды И всех подкоманд, чтобы
    # `dsh-docker-helper.py <cmd> --json` работало единообразно.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--json", action="store_true",
        help="машиночитаемый вывод где возможно",
    )
    common.add_argument(
        "--debug", action="store_true",
        help="печатать выполняемый docker-вызов в stderr",
    )

    p = argparse.ArgumentParser(
        description="Гельпер-мост DSH <-> Docker для WERP.",
        parents=[common],
    )
    # Команда хранится в отдельном dest (cmd), чтобы не конфликтовать
    # с позиционным аргументом `command` подкоманды exec.
    sub = p.add_subparsers(dest="cmd", required=True)

    ps = sub.add_parser("ps", help="список контейнеров", parents=[common])
    ps.add_argument("--raw", action="store_true", help="сырой вывод docker")

    sub.add_parser("health", help="статус сервисов compose", parents=[common])

    plog = sub.add_parser("logs", help="хвост логов контейнера",
                          parents=[common])
    plog.add_argument("container", nargs="?", help="имя контейнера")
    plog.add_argument("--tail", default="100", help="кол-во строк")
    plog.add_argument("--follow", action="store_true", help="follow mode")

    pexec = sub.add_parser("exec", help="команда внутри контейнера",
                           parents=[common])
    pexec.add_argument("container", nargs="?", help="имя контейнера")
    pexec.add_argument("command", nargs=argparse.REMAINDER,
                       help="команда и аргументы")
    pexec.add_argument("--it", action="store_true", help="интерактивный (-it)")

    pcomp = sub.add_parser(
        "compose",
        help="управление стеком: up|down|stop|restart",
        parents=[common],
    )
    pcomp.add_argument("action", choices=["up", "down", "stop", "restart"])
    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "ps": cmd_ps,
        "health": cmd_health,
        "logs": cmd_logs,
        "exec": cmd_exec,
        "compose": cmd_compose,
    }
    fn = dispatch.get(args.cmd)
    if not fn:
        parser.print_help()
        return 2
    return fn(args)


if __name__ == "__main__":
    sys.exit(main())