"""Testes das ferramentas Python: preservação e transferência, sem MySQL externo."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import manage
from tools.verify_legacy_password import verify


class MigrationTools(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.source = self.directory / "dados antigos #1.sqlite3"
        with sqlite3.connect(self.source) as d:
            d.executescript('''CREATE TABLE users(id INTEGER PRIMARY KEY,name,email,password,role,trainer,goal);
CREATE TABLE plans(id INTEGER PRIMARY KEY,student,kind,title,items);
CREATE TABLE logs(id INTEGER PRIMARY KEY,student,kind,data,date);
CREATE TABLE workout_runs(session PRIMARY KEY,student,plan,snapshot,exercises,status,log,updated);
CREATE TABLE sessions(token,user,expires);''')
            d.execute("INSERT INTO users VALUES(1,?,?,?,?,?,?)", ("Lívia", "personal@example.test", "hash-original", "personal", None, "Força"))
            d.execute("INSERT INTO users VALUES(2,?,?,?,?,?,?)", ("Ana", "aluna@example.test", "outro-hash", "aluno", 1, "Força"))
            self.items = json.dumps([dict(name="Cadeira extensora", sets=3, reps="12", load=20, rest=60)])
            d.execute("INSERT INTO plans VALUES(7,2,'workout',?,?)", ("Quadríceps", self.items))
            d.execute("INSERT INTO logs VALUES(9,2,'measurement',?,?)", ('{"weight":70}', "2026-11-01 10:00:00"))
            d.execute("INSERT INTO workout_runs VALUES('run-1',2,7,?,?,'active',NULL,?)", (self.items, '[{"load":22.5,"done":true}]', "2026-11-01 12:00:00"))
            d.execute("INSERT INTO sessions VALUES('never-export-this-session',2,99999999999)")

    def tearDown(self):
        self.temp.cleanup()

    def test_readonly_export_preserves_ids_json_and_drops_auth_sessions(self):
        before = self.source.read_bytes()
        data = manage.export_sqlite(self.source)
        self.assertEqual(data["format"], "evofit-sqlite")
        self.assertEqual(data["version"], 1)
        self.assertEqual(data["users"][0]["password"], "hash-original")
        self.assertEqual(data["plans"][0]["id"], 7)
        self.assertEqual(data["plans"][0]["items"], self.items)
        self.assertEqual(data["logs"][0]["date"], "2026-11-01 10:00:00")
        self.assertEqual(data["workout_runs"][0]["session"], "run-1")
        self.assertNotIn("sessions", data)
        self.assertNotIn("never-export-this-session", json.dumps(data))
        self.assertEqual(before, self.source.read_bytes())
        connection = manage.source_connection(self.source)
        try:
            with self.assertRaises(sqlite3.OperationalError):
                connection.execute("DELETE FROM users")
        finally:
            connection.close()

    def test_consistent_backup_survives_changes_and_never_overwrites_previous_backup(self):
        data, backup = manage.prepare_migration(self.source, self.directory / "backups")
        self.assertTrue(backup.is_file())
        self.assertEqual(manage.export_sqlite(backup), data)
        with sqlite3.connect(self.source) as d:
            d.execute("UPDATE users SET name='Depois' WHERE id=1")
        self.assertEqual(manage.export_sqlite(backup)["users"][0]["name"], "Lívia")
        _, newer = manage.prepare_migration(self.source, self.directory / "backups")
        self.assertNotEqual(backup, newer)
        self.assertEqual(manage.export_sqlite(backup)["users"][0]["name"], "Lívia")

    def test_missing_invalid_and_old_schema_do_not_create_source(self):
        missing = self.directory / "ausente.sqlite3"
        with self.assertRaises(manage.ToolError):
            manage.export_sqlite(missing)
        self.assertFalse(missing.exists())
        invalid = self.directory / "invalido.sqlite3"
        invalid.write_text("não é SQLite")
        with self.assertRaises(manage.ToolError):
            manage.export_sqlite(invalid)
        with sqlite3.connect(self.source) as d:
            d.execute("DROP TABLE workout_runs")
        self.assertEqual(manage.export_sqlite(self.source)["workout_runs"], [])
        with sqlite3.connect(self.source) as d:
            d.execute("DROP TABLE users")
        with self.assertRaises(manage.ToolError):
            manage.export_sqlite(self.source)

    def test_migration_initializes_without_seed_and_uses_stdin_not_argv(self):
        calls = []
        def fake_run(command, **kwargs):
            calls.append((command, kwargs))
            return subprocess.CompletedProcess(command, 0)
        output = io.StringIO()
        with mock.patch.object(manage.subprocess, "run", side_effect=fake_run), contextlib.redirect_stdout(output):
            backup = manage.migrate("/test/php", self.source, backup_dir=self.directory / "backups", create_database=True)
        self.assertTrue(backup.is_file())
        self.assertEqual(calls[0][0][-2:], ["--create-database", "--no-seed"])
        self.assertTrue(calls[1][0][1].endswith("import_sqlite.php"))
        self.assertNotIn("hash-original", " ".join(calls[1][0]))
        self.assertEqual(json.loads(calls[1][1]["input"])["users"][0]["password"], "hash-original")
        self.assertNotIn("hash-original", output.getvalue())
        self.assertNotIn("personal@example.test", output.getvalue())
        self.assertEqual(calls[1][1]["env"]["PYTHON_BIN"], os.environ.get("PYTHON_BIN", sys.executable))

    def test_php_failure_does_not_change_or_remove_source_or_backup(self):
        before = self.source.read_bytes()
        result = subprocess.CompletedProcess(["php"], 1)
        with mock.patch.object(manage.subprocess, "run", return_value=result), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(manage.ToolError):
                manage.migrate("php", self.source, backup_dir=self.directory / "backups")
        self.assertEqual(before, self.source.read_bytes())
        backups = list((self.directory / "backups").glob("*.sqlite3"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(manage.export_sqlite(backups[0]), manage.export_sqlite(self.source))

    def test_php_resolution_and_port_validation(self):
        with mock.patch.object(manage.shutil, "which", return_value=None):
            with self.assertRaises(manage.ToolError):
                manage.resolve_php(str(self.directory / "missing-php"))
        self.assertEqual(manage.port_number("4173"), 4173)
        for value in ["0", "65536", "abc"]:
            with self.assertRaises(Exception):
                manage.port_number(value)


class LegacyPasswords(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.salt = "0123456789abcdef0123456789abcdef"
        cls.value = "EvoFit123!"
        cls.stored = cls.salt + ":" + hashlib.scrypt(cls.value.encode(), salt=cls.salt.encode(), n=16384, r=8, p=1).hex()

    def test_verifies_actual_legacy_hash_but_not_invalid_input(self):
        self.assertTrue(verify(dict(password=self.value, hash=self.stored)))
        for data in [dict(password="errada", hash=self.stored), dict(password=self.value, hash="invalido"), dict(password=123, hash=self.stored), dict(password="a" * 4097, hash=self.stored), [], None]:
            self.assertFalse(verify(data))

    def test_cli_never_echoes_password_or_hash(self):
        script = Path(__file__).resolve().parents[1] / "tools" / "verify_legacy_password.py"
        for payload, expected in [(json.dumps(dict(password=self.value, hash=self.stored)), "1"), ("not json", "0"), ('"' + 'a' * 17000 + '"', "0")]:
            result = subprocess.run([sys.executable, str(script)], input=payload, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, expected)
            self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
