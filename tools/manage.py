#!/usr/bin/env python3
"""Inicialização PHP/MySQL e migração preservando os dados do EvoFit antigo."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


class ToolError(Exception):
    """Falha que pode ser mostrada sem expor credenciais ou conteúdo do banco."""


def resolve_php(configured: str | None = None) -> str:
    candidate = configured or os.environ.get("EVOFIT_PHP_BIN")
    if candidate:
        found = shutil.which(candidate)
        if found:
            return found
        path = Path(candidate).expanduser()
        if path.is_file():
            return str(path.resolve())
        raise ToolError("O executável PHP configurado não foi encontrado. Confira EVOFIT_PHP_BIN.")
    found = shutil.which("php")
    if found:
        return found
    xampp = Path(r"C:\xampp\php\php.exe")
    if os.name == "nt" and xampp.is_file():
        return str(xampp)
    raise ToolError("PHP não encontrado. Instale PHP 8.2+ com PDO MySQL (ou XAMPP) e configure EVOFIT_PHP_BIN se necessário.")


def php_environment() -> dict[str, str]:
    result = dict(os.environ)
    result.setdefault("PYTHON_BIN", sys.executable)
    return result


def run_php(php: str, script: str, *arguments: str, payload: str | None = None) -> None:
    command = [php, str(ROOT / "php" / script), *arguments]
    try:
        result = subprocess.run(command, cwd=ROOT, env=php_environment(), input=payload, text=True, check=False)
    except OSError as exc:
        raise ToolError("Não foi possível executar o PHP. Confira sua instalação.") from exc
    if result.returncode:
        raise ToolError("A operação PHP não foi concluída. Confira a mensagem acima e as configurações do MySQL.")


def source_connection(path: Path) -> sqlite3.Connection:
    source = path.expanduser().resolve()
    if not source.is_file():
        raise ToolError("O banco SQLite antigo não foi encontrado. Confira o caminho informado.")
    connection = None
    try:
        connection = sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        connection.execute("SELECT name FROM sqlite_master LIMIT 1").fetchall()
        return connection
    except sqlite3.Error as exc:
        if connection is not None:
            connection.close()
        raise ToolError("O arquivo informado não é um banco SQLite válido ou não pode ser lido.") from exc


def export_connection(connection: sqlite3.Connection) -> dict:
    """Retorna dados de migração em memória; nunca inclui sessões de autenticação."""
    tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    mandatory = {"users", "plans", "logs"}
    if not mandatory.issubset(tables):
        raise ToolError("O SQLite não contém as tabelas esperadas do EvoFit.")
    fields = {
        "users": ("id", "name", "email", "password", "role", "trainer", "goal"),
        "plans": ("id", "student", "kind", "title", "items"),
        "logs": ("id", "student", "kind", "data", "date"),
        "workout_runs": ("session", "student", "plan", "snapshot", "exercises", "status", "log", "updated"),
    }
    result = {"format": "evofit-sqlite", "version": 1}
    try:
        for table, names in fields.items():
            if table not in tables:
                result[table] = []
                continue
            # Identificadores vêm apenas desta lista constante, não de dados do usuário.
            columns = ",".join('"' + name + '"' for name in names)
            order = '"session"' if table == "workout_runs" else '"id"'
            rows = connection.execute(f'SELECT {columns} FROM "{table}" ORDER BY {order}').fetchall()
            result[table] = [dict(row) for row in rows]
    except sqlite3.Error as exc:
        raise ToolError("A estrutura do SQLite não corresponde à versão esperada do EvoFit.") from exc
    return result


def export_sqlite(path: Path) -> dict:
    """Exportação somente de leitura para uso interno e testes."""
    connection = source_connection(path)
    try:
        connection.execute("BEGIN")
        return export_connection(connection)
    finally:
        connection.close()


def prepare_migration(path: Path, backup_dir: Path | None = None) -> tuple[dict, Path]:
    """Faz backup consistente, valida e exporta exatamente a cópia preservada."""
    source = path.expanduser().resolve()
    destination = (backup_dir or ROOT / "backups").expanduser().resolve()
    connection = source_connection(source)
    backup_path: Path | None = None
    try:
        destination.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        descriptor, filename = tempfile.mkstemp(prefix=f"{source.stem}-{stamp}-", suffix=".sqlite3", dir=destination)
        os.close(descriptor)
        backup_path = Path(filename)
        backup_connection = sqlite3.connect(backup_path)
        try:
            connection.backup(backup_connection)
        finally:
            backup_connection.close()
        os.chmod(backup_path, 0o600)
        # A validação usa a cópia; futuras gravações no banco antigo não alteram a migração.
        data = export_sqlite(backup_path)
        return data, backup_path
    except (OSError, sqlite3.Error) as exc:
        raise ToolError("Não foi possível criar o backup. O banco original foi mantido.") from exc
    finally:
        connection.close()


def init_database(php: str, *, create_database: bool = False, seed: bool = True) -> None:
    args = []
    if create_database:
        args.append("--create-database")
    if not seed:
        args.append("--no-seed")
    run_php(php, "setup.php", *args)


def migrate(php: str, source: Path, *, backup_dir: Path | None = None, create_database: bool = False) -> Path:
    # Nenhuma escrita no MySQL ocorre antes de preservar e validar o SQLite.
    payload, backup_path = prepare_migration(source, backup_dir)
    print(f"Backup do banco antigo preservado em: {backup_path}")
    init_database(php, create_database=create_database, seed=False)
    # Senhas/ hashes e demais dados seguem por stdin, nunca na linha de comando ou logs.
    run_php(php, "import_sqlite.php", payload=json.dumps(payload, ensure_ascii=False, allow_nan=False))
    print("Migração concluída. O SQLite original foi mantido; o sistema agora pode usar o MySQL.")
    return backup_path


def serve(php: str, host: str, port: int) -> int:
    run_php(php, "setup.php", "--check")
    command = [php, "-S", f"{host}:{port}", "-t", str(ROOT / "static"), str(ROOT / "router.php")]
    print(f"EvoFit iniciado na porta {port}. Mantenha esta janela aberta.", flush=True)
    print("Para parar, pressione Ctrl+C. O serviço MySQL também precisa continuar ligado.", flush=True)
    try:
        return subprocess.call(command, cwd=ROOT, env=php_environment())
    except KeyboardInterrupt:
        print("\nEvoFit encerrado. Os dados permanecem no MySQL.")
        return 0
    except OSError as exc:
        raise ToolError("Não foi possível iniciar o servidor PHP.") from exc


def port_number(value: str) -> int:
    try:
        port = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Informe uma porta numérica.") from exc
    if not 1 <= port <= 65535:
        raise argparse.ArgumentTypeError("A porta deve estar entre 1 e 65535.")
    return port


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EvoFit: preparar e executar a versão PHP/MySQL.")
    parser.add_argument("--php", help="Caminho do executável PHP; também pode usar EVOFIT_PHP_BIN.")
    sub = parser.add_subparsers(dest="command", required=True)
    initialization = sub.add_parser("init", help="Criar as tabelas e os dados demo sem apagar registros existentes.")
    initialization.add_argument("--create-database", action="store_true", help="Criar também o banco definido em DB_NAME (requer permissão).")
    initialization.add_argument("--no-seed", action="store_true", help="Criar somente tabelas, sem contas de demonstração.")
    sub.add_parser("check", help="Conferir PHP, PDO MySQL e conexão/configuração do banco.")
    running = sub.add_parser("serve", help="Iniciar o site com PHP; o MySQL precisa estar ligado.")
    running.add_argument("--host", default="127.0.0.1")
    running.add_argument("--port", type=port_number, default=4173)
    migration = sub.add_parser("migrate-sqlite", help="Preservar e importar o SQLite antigo para um MySQL vazio.")
    migration.add_argument("source", type=Path, nargs="?", default=ROOT / "evofit.sqlite3")
    migration.add_argument("--backup-dir", type=Path, help="Pasta para a cópia de segurança (padrão: backups/).")
    migration.add_argument("--create-database", action="store_true", help="Criar DB_NAME se ainda não existir (requer permissão).")
    args = parser.parse_args(argv)
    try:
        php = resolve_php(args.php)
        if args.command == "init":
            init_database(php, create_database=args.create_database, seed=not args.no_seed)
        elif args.command == "check":
            run_php(php, "setup.php", "--check")
        elif args.command == "serve":
            return serve(php, args.host, args.port)
        else:
            migrate(php, args.source, backup_dir=args.backup_dir, create_database=args.create_database)
        return 0
    except ToolError as exc:
        print(f"Não foi possível concluir: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperação interrompida. O SQLite original foi mantido.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
