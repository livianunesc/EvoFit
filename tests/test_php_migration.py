"""Real MySQL migration test: requires a separate, explicitly selected EMPTY database.

    EVOFIT_MIGRATION_PHP=/path/to/php-for-empty-db \
    EVOFIT_MIGRATION_URL=http://127.0.0.1:4186 \
    python3 tests/test_php_migration.py

The supplied PHP executable/wrapper must select the SAME dedicated database as
EVOFIT_MIGRATION_URL. No tables are truncated, records deleted, or user DBs reset.
The test refuses nonempty databases before importing its temporary legacy fixture.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from legacy import server_sqlite as legacy
from tools import manage
from test_php_flow import ApiClient

TABLE_FIELDS = {
    'users': ('id', 'name', 'email', 'password', 'role', 'trainer', 'goal'),
    'plans': ('id', 'student', 'kind', 'title', 'items'),
    'logs': ('id', 'student', 'kind', 'data', 'date'),
    'workout_runs': ('session', 'student', 'plan', 'snapshot', 'exercises', 'status', 'log', 'updated'),
}


class PhpMigration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.php = os.environ.get('EVOFIT_MIGRATION_PHP')
        cls.url = os.environ.get('EVOFIT_MIGRATION_URL')
        if not cls.php or not cls.url:
            raise unittest.SkipTest('Migração MySQL não executada: defina EVOFIT_MIGRATION_PHP e EVOFIT_MIGRATION_URL para um alvo vazio e isolado.')

    def php_run(self, arguments, payload=None):
        env = dict(os.environ)
        env.setdefault('PYTHON_BIN', sys.executable)
        return subprocess.run([self.php, *arguments], cwd=ROOT, env=env,
                              input=json.dumps(payload, ensure_ascii=False) if payload is not None else None,
                              text=True, capture_output=True, timeout=40, check=False)

    def probe(self):
        code = """require 'php/bootstrap.php';$db=evo_db();evo_schema($db);$counts=[];
        foreach(['users','plans','logs','workout_runs','sessions'] as $table){$counts[$table]=(int)$db->query('SELECT COUNT(*) FROM `'.$table.'`')->fetchColumn();}
        echo json_encode(['database'=>$db->query('SELECT DATABASE()')->fetchColumn(),'counts'=>$counts]);"""
        result = self.php_run(['-r', code])
        self.assertEqual(result.returncode, 0, 'Não foi possível consultar o MySQL de teste.')
        return json.loads(result.stdout)

    def assert_mysql_matches(self, payload):
        # Compare privately in PHP so a failing assertion never dumps password hashes or user rows.
        code = """require 'php/bootstrap.php';$db=evo_db();$input=json_decode(stream_get_contents(STDIN),true);$ok=true;
        foreach($input['fields'] as $table=>$fields){
          $select=implode(',',array_map(fn($name)=>'`'.$name.'`',$fields));
          $key=$table==='workout_runs'?'session':'id';
          $rows=$db->query('SELECT '.$select.' FROM `'.$table.'` ORDER BY `'.$key.'`')->fetchAll();
          $expected=$input['payload'][$table];
          if(count($rows)!==count($expected)){$ok=false;continue;}
          foreach($rows as $i=>$row){foreach($fields as $field){
            $actual=$row[$field];$value=$expected[$i][$field];
            if(($actual===null)!==($value===null) || ($value!==null && (string)$actual!==(string)$value)){$ok=false;}
          }}
        }
        $sessionCount=(int)$db->query('SELECT COUNT(*) FROM sessions')->fetchColumn();
        echo json_encode(['identical'=>$ok,'sessions'=>$sessionCount]);"""
        result = self.php_run(['-r', code], {'fields': TABLE_FIELDS, 'payload': payload})
        self.assertEqual(result.returncode, 0, 'A comparação privada da migração falhou.')
        summary = json.loads(result.stdout)
        self.assertTrue(summary['identical'], 'IDs, hashes, datas, planos, históricos ou sessões de treino não foram preservados exatamente.')
        self.assertEqual(summary['sessions'], 0, 'Sessões antigas de autenticação não podem ser copiadas.')

    def legacy_fixture(self, path):
        previous = legacy.DB
        try:
            legacy.DB = str(path)
            legacy.init()
            with legacy.connect() as db:
                plan = db.execute("SELECT * FROM plans WHERE kind='workout' ORDER BY id LIMIT 1").fetchone()
                items = json.loads(plan['items'])
                active = [dict(load=22.5, done=True), dict(load=60, done=False)]
                completed = [dict(load=25, done=True), dict(load=65, done=True)]
                log_data = dict(title=plan['title'], exercises=[dict(name=item['name'], **entry)
                                                              for item, entry in zip(items, completed)],
                                notes='Registro legado concluído')
                db.execute('INSERT INTO logs(id,student,kind,data,date) VALUES(401,2,?,?,?)',
                           ('workout', json.dumps(log_data, ensure_ascii=False), '2026-11-03 12:13:14'))
                db.execute('INSERT INTO workout_runs VALUES(?,?,?,?,?,?,?,?)',
                           ('active-partial-legacy', 2, plan['id'], json.dumps(items, ensure_ascii=False),
                            json.dumps(active), 'active', None, '2026-11-04 08:15:30'))
                db.execute('INSERT INTO workout_runs VALUES(?,?,?,?,?,?,?,?)',
                           ('completed-legacy', 2, plan['id'], json.dumps(items, ensure_ascii=False),
                            json.dumps(completed), 'completed', 401, '2026-11-03 12:13:14'))
                old_items = [dict(item) for item in items]
                old_items[0]['reps'] = '15'
                db.execute('INSERT INTO workout_runs VALUES(?,?,?,?,?,?,?,?)',
                           ('invalidated-legacy', 2, plan['id'], json.dumps(old_items, ensure_ascii=False),
                            json.dumps(active), 'invalidated', None, '2026-11-02 07:00:00'))
                diet = db.execute("SELECT items FROM plans WHERE kind='diet' LIMIT 1").fetchone()['items']
                db.execute('INSERT INTO plans(id,student,kind,title,items) VALUES(1001,2,?,?,?)',
                           ('diet', 'Plano legado com identificador preservado', diet))
                # Synthetic auth session proves that migration excludes login sessions.
                db.execute('INSERT INTO sessions VALUES(?,?,?)', ('synthetic-do-not-copy', 2, time.time()+86400))
            return plan['id']
        finally:
            legacy.DB = previous

    def test_atomic_legacy_import_preserves_all_run_states_and_login(self):
        initial = self.probe()
        self.assertTrue(all(n == 0 for n in initial['counts'].values()),
                        'ALVO NÃO VAZIO: use um novo banco dedicado. Nenhum dado foi apagado ou importado.')
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp)/'legacy.sqlite3'
            plan_id = self.legacy_fixture(source)
            digest = hashlib.sha256(source.read_bytes()).digest()
            payload, backup = manage.prepare_migration(source, Path(temp)/'backups')
            self.assertTrue(backup.is_file())
            self.assertTrue(manage.export_sqlite(backup) == payload, 'O backup não corresponde aos dados exportados.')
            self.assertTrue(hashlib.sha256(source.read_bytes()).digest() == digest, 'A preparação alterou o SQLite original.')
            self.assertNotIn('sessions', payload)
            self.assertEqual({row['status'] for row in payload['workout_runs']}, {'active', 'completed', 'invalidated'})

            # Invalid references are rejected before any writes.
            invalid = copy.deepcopy(payload)
            invalid['plans'][0]['student'] = 999999
            result = self.php_run([str(ROOT/'php/import_sqlite.php')], invalid)
            self.assertNotEqual(result.returncode, 0, 'Uma referência inválida foi aceita.')
            self.assertTrue(all(n == 0 for n in self.probe()['counts'].values()), 'A validação inválida escreveu registros.')

            # A valid envelope that exceeds MySQL TEXT capacity forces a real SQL failure
            # after an earlier user insert; the transaction must roll that insert back.
            too_large = copy.deepcopy(payload)
            too_large['users'][-1]['goal'] = 'X' * 70000
            result = self.php_run([str(ROOT/'php/import_sqlite.php')], too_large)
            self.assertNotEqual(result.returncode, 0, 'O alvo de teste não está em modo estrito ou permitiu campo inválido.')
            self.assertTrue(all(n == 0 for n in self.probe()['counts'].values()), 'Uma falha SQL deixou importação parcial.')

            result = self.php_run([str(ROOT/'php/import_sqlite.php')], payload)
            self.assertEqual(result.returncode, 0, 'A importação válida falhou; confira o serviço MySQL e a configuração de teste.')
            imported = json.loads(result.stdout)
            self.assertTrue(imported.get('ok'))
            self.assertEqual(imported['imported'], {table: len(payload[table]) for table in TABLE_FIELDS})
            self.assert_mysql_matches(payload)
            result = self.php_run([str(ROOT/'php/import_sqlite.php')], payload)
            self.assertNotEqual(result.returncode, 0, 'Uma segunda migração não pode sobrescrever um banco preenchido.')
            self.assert_mysql_matches(payload)

            client = ApiClient(self.url)
            self.assertTrue(client.login('aluno@evofit.demo', 'aluno')['ok'])
            state = client.request('state')
            self.assertEqual(state['user']['id'], 2)
            self.assertEqual({plan['id'] for plan in state['plans']}, {plan['id'] for plan in payload['plans']})
            self.assertEqual({(log['id'], log['date']) for log in state['logs']},
                             {(log['id'], log['date']) for log in payload['logs']})
            self.assertEqual(len(state['workoutProgress']), 1)
            progress = state['workoutProgress'][0]
            self.assertEqual(progress['session'], 'active-partial-legacy')
            self.assertEqual(progress['exercises'], [dict(load=22.5, done=True), dict(load=60, done=False)])
            self.assertEqual(progress['updated'], '2026-11-04 08:15:30')
            plan = next(plan for plan in state['plans'] if plan['id'] == plan_id)
            self.assertEqual(plan['version'], legacy.workout_version(json.loads(next(p['items'] for p in payload['plans'] if p['id'] == plan_id))))
            # The same old snapshot must remain usable by the new completion API.
            client.request('exercise', {'plan': plan_id, 'version': plan['version'], 'session': progress['session'],
                                        'index': 1, 'load': 62.5, 'done': True})
            client.request('workout/complete', {'plan': plan_id, 'session': progress['session'], 'notes': 'Retomado após migração'})
            self.assertEqual(client.request('state')['workoutProgress'], [])
            self.assertEqual(len(client.request('state')['logs']), len(payload['logs'])+1)

            # Confirm rehash without exposing either old or new hashes in output.
            verification = self.php_run(['-r', "require 'php/bootstrap.php';$db=evo_db();$hash=$db->query('SELECT password FROM users WHERE id=2')->fetchColumn();echo json_encode(['rehash'=>str_starts_with($hash,'sha256:')]);"])
            self.assertEqual(verification.returncode, 0)
            self.assertTrue(json.loads(verification.stdout)['rehash'], 'O login legado não atualizou o hash com segurança.')
            self.assertTrue(hashlib.sha256(source.read_bytes()).digest() == digest, 'A migração alterou o SQLite original.')


if __name__ == '__main__':
    if not os.environ.get('EVOFIT_MIGRATION_PHP') or not os.environ.get('EVOFIT_MIGRATION_URL'):
        raise SystemExit('Defina EVOFIT_MIGRATION_PHP e EVOFIT_MIGRATION_URL para o mesmo MySQL vazio e isolado.')
    unittest.main(verbosity=2)
