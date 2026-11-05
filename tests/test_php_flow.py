"""PHP/MySQL integration checks against an explicitly configured test instance.

The suite creates accounts with unique test emails and never deletes existing records.
Run only against a dedicated test database:
    EVOFIT_TEST_URL=http://127.0.0.1:4174 python3 tests/test_php_flow.py
"""
import http.cookiejar
import json
import os
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor


class ApiClient:
    def __init__(self, base):
        self.base = base.rstrip('/') + '/'
        self.cookies = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, route, payload=None, *, method=None, headers=None):
        # Query routing also works when deployed below an Apache/XAMPP subdirectory.
        url = self.base + 'api.php?route=' + urllib.parse.quote(route, safe='')
        data = json.dumps(payload, ensure_ascii=False).encode() if payload is not None else None
        request = urllib.request.Request(url, data=data, method=method,
                                         headers={'Content-Type': 'application/json', **(headers or {})})
        with self.opener.open(request, timeout=20) as response:
            return json.load(response)

    def login(self, email, role, password='EvoFit123!'):
        return self.request('login', {'email': email, 'role': role, 'password': password})


class PhpFlow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = os.environ.get('EVOFIT_TEST_URL', '').rstrip('/') + '/'
        if not os.environ.get('EVOFIT_TEST_URL'):
            raise unittest.SkipTest('EVOFIT_TEST_URL is required; PHP/MySQL checks were not run.')

    def client(self):
        return ApiClient(self.base)

    def assert_error(self, client, route, payload=None, status=400, **kwargs):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            client.request(route, payload, **kwargs)
        error = caught.exception
        self.assertIn(error.code, status if isinstance(status, tuple) else (status,))
        body = json.load(error)
        self.assertIsInstance(body.get('error'), str)
        self.assertTrue(body['error'])
        return body

    def training_fixture(self):
        suffix = uuid.uuid4().hex
        trainer_email, student_email = f'trainer-{suffix}@example.com', f'student-{suffix}@example.com'
        trainer, student = self.client(), self.client()
        trainer.request('register', {'name': 'Personal de integração', 'email': trainer_email,
                                     'password': 'Teste123!', 'role': 'personal'})
        trainer.request('student', {'name': 'Aluno de integração', 'email': student_email,
                                    'password': 'Teste123!', 'goal': 'Ganhar força'})
        person = next(s for s in trainer.request('state')['students'] if s['email'] == student_email)
        items = [dict(name='Cadeira extensora', sets=3, reps='12', load=15, rest=60,
                      notes='Controle a descida.', illustration='extension'),
                 dict(name='Agachamento', sets=3, reps='10', load=20, rest=90, notes='')]
        trainer.request('plan', {'student': person['id'], 'kind': 'workout', 'title': 'Quadríceps', 'items': items})
        trainer.request('plan', {'student': person['id'], 'kind': 'diet', 'title': 'Plano equilibrado',
                                'items': [dict(name='Almoço', time='12:30', food='Arroz, feijão e frango',
                                               quantity='100 g, 80 g e 120 g')]})
        student.login(student_email, 'aluno', 'Teste123!')
        plan = next(p for p in student.request('state')['plans'] if p['kind'] == 'workout')
        return trainer, student, person['id'], plan, student_email

    def exercise(self, client, plan, index=0, load=17.5, done=True, session=None):
        payload = {'plan': plan['id'], 'version': plan['version'], 'index': index, 'load': load, 'done': done}
        if session:
            payload['session'] = session
        return client.request('exercise', payload)['progress']

    def test_demo_authentication_and_safe_state(self):
        for email, role in [('personal@evofit.demo', 'personal'), ('aluno@evofit.demo', 'aluno')]:
            with self.subTest(role=role):
                client = self.client()
                self.assert_error(client, 'state', status=401)
                self.assertTrue(client.login(email, role)['ok'])
                state = client.request('state')
                self.assertEqual(state['user']['role'], role)
                self.assertGreaterEqual(len(state['students']), 1)
                self.assertGreaterEqual(len(state['plans']), 3)
                self.assertNotIn('password', state['user'])
                self.assertIn('workoutProgress', state)
                self.assertTrue(all('password' not in item for item in state['students']))
                cookie = next(iter(client.cookies))
                self.assertTrue(cookie.has_nonstandard_attr('HttpOnly'))
                self.assertEqual(cookie.get_nonstandard_attr('SameSite'), 'Strict')
                client.request('logout', {})
                self.assert_error(client, 'state', status=401)

    def test_invalid_auth_and_duplicate_registration(self):
        client = self.client()
        self.assert_error(client, 'login', {'email': 'aluno@evofit.demo', 'password': 'errada123', 'role': 'aluno'}, 401)
        self.assert_error(client, 'login', {'email': 'aluno@evofit.demo', 'password': 'EvoFit123!', 'role': 'personal'}, 401)
        self.assert_error(client, 'register', {'name': 'Duplicado', 'email': 'aluno@evofit.demo',
                                             'password': 'Teste123!', 'role': 'aluno'})
        self.assert_error(client, 'register', {'name': '', 'email': 'inválido', 'password': '123', 'role': 'aluno'})

    def test_plans_profile_measurements_and_personal_visibility(self):
        trainer, student, sid, plan, _ = self.training_fixture()
        state = student.request('state')
        self.assertEqual([s['id'] for s in state['students']], [sid])
        self.assertEqual({p['kind'] for p in state['plans']}, {'workout', 'diet'})
        self.assertEqual(next(p for p in state['plans'] if p['kind'] == 'diet')['items'][0]['time'], '12:30')
        self.assertEqual(len(plan['version']), 64)
        trainer.request('plan', dict(plan, title='Terça · Quadríceps'))
        self.assertEqual(next(p for p in student.request('state')['plans'] if p['id'] == plan['id'])['title'], 'Terça · Quadríceps')
        student.request('profile', {'name': 'Aluno atualizado', 'goal': 'Resistência'})
        student.request('log', {'kind': 'measurement', 'data': dict(weight=70, waist=80, hip=95, chest=90)})
        observed = trainer.request('state')
        self.assertEqual(next(s for s in observed['students'] if s['id'] == sid)['name'], 'Aluno atualizado')
        log = next(log for log in observed['logs'] if log['student'] == sid)
        self.assertEqual(log['kind'], 'measurement')
        self.assertEqual(log['data']['weight'], 70)

    def test_resume_and_idempotent_workout_completion(self):
        trainer, student, sid, plan, email = self.training_fixture()
        progress = self.exercise(student, plan)
        session = progress['session']
        self.assertEqual(progress['exercises'], [dict(load=17.5, done=True), dict(load=20, done=False)])
        second = self.client()
        second.login(email, 'aluno', 'Teste123!')
        self.assertEqual(second.request('state')['workoutProgress'][0], progress)
        self.assertEqual(next(x for x in trainer.request('state')['workoutProgress'] if x['student'] == sid), progress)
        self.assert_error(student, 'workout/complete', {'plan': plan['id'], 'session': session})
        self.exercise(student, plan, load=18, done=False, session=session)
        self.assertFalse(second.request('state')['workoutProgress'][0]['exercises'][0]['done'])
        self.exercise(student, plan, load=18, session=session)
        self.exercise(student, plan, index=1, load=25, session=session)
        payload = {'plan': plan['id'], 'session': session, 'notes': 'Treino de integração concluído'}
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda c: c.request('workout/complete', payload), (student, second)))
        self.assertEqual(results[0]['log'], results[1]['log'])
        self.assertEqual(sorted(r['alreadyCompleted'] for r in results), [False, True])
        current = student.request('state')
        self.assertEqual(current['workoutProgress'], [])
        self.assertEqual(len(current['logs']), 1)
        self.assertEqual(current['logs'][0]['data']['exercises'], [dict(name='Cadeira extensora', load=18, done=True),
                                                                 dict(name='Agachamento', load=25, done=True)])
        self.assertEqual(current['logs'][0]['data']['notes'], payload['notes'])
        self.assertEqual(len([log for log in trainer.request('state')['logs'] if log['student'] == sid]), 1)
        next_run = self.exercise(student, plan, load=20)
        self.assertNotEqual(next_run['session'], session)
        self.assertFalse(next_run['exercises'][1]['done'])

    def test_permissions_and_payload_validation(self):
        trainer, student, sid, plan, _ = self.training_fixture()
        outsider = self.client()
        outsider.login('aluno@evofit.demo', 'aluno')
        payload = {'plan': plan['id'], 'version': plan['version'], 'index': 0, 'load': 20, 'done': True}
        for client in (trainer, outsider):
            self.assert_error(client, 'exercise', payload, (403, 404))
        self.assert_error(student, 'exercise', dict(payload, student=1), 403)
        for patch in [dict(index=-1), dict(index=2), dict(index=True), dict(load=-1), dict(load=2000),
                      dict(load=True), dict(load=float('nan')), dict(load=float('inf')), dict(load='not-a-number'), dict(done='true')]:
            with self.subTest(patch=patch):
                self.assert_error(student, 'exercise', dict(payload, **patch))
        self.assertEqual(student.request('state')['workoutProgress'], [])
        plans_before = trainer.request('state')['plans']
        for reps in [[], {}, True, False, None]:
            with self.subTest(malformed_reps=reps):
                malformed = [dict(item) for item in plan['items']]
                malformed[0]['reps'] = reps
                self.assert_error(trainer, 'plan', dict(plan, items=malformed))
        self.assertTrue(trainer.request('state')['plans'] == plans_before, 'Invalid repetitions changed the plan.')
        self.assert_error(student, 'exercise', {k:v for k,v in payload.items() if k!='version'}, 409)
        self.assert_error(student, 'exercise', status=405)
        self.assert_error(student, 'student', {'name': 'Indevido', 'email': 'x@example.com', 'password': 'Teste123!'}, 403)
        self.assert_error(student, 'plan', dict(plan, title='Indevido'), 403)
        self.assert_error(student, 'log', {'student': 1, 'kind': 'measurement', 'data': {}}, 403)
        other = self.client()
        other.request('register', {'name': 'Personal isolado', 'email': f'isolated-{uuid.uuid4().hex}@example.com',
                                   'password': 'Teste123!', 'role': 'personal'})
        self.assertEqual(other.request('state')['students'], [])
        self.assert_error(other, 'plan', dict(plan, title='Indevido'), (403, 404))
        self.assert_error(student, 'profile', {'name': 'Ataque'}, 403, headers={'Sec-Fetch-Site': 'cross-site'})

    def test_plan_changes_reject_stale_pages_and_runs(self):
        trainer, student, sid, plan, _ = self.training_fixture()
        updated_items = [dict(item) for item in plan['items']]
        updated_items.reverse()
        trainer.request('plan', dict(plan, items=updated_items))
        self.assert_error(student, 'exercise', {'plan': plan['id'], 'version': plan['version'], 'index': 0,
                                               'load': 20, 'done': True}, 409)
        self.assertEqual(student.request('state')['workoutProgress'], [])
        plan = next(p for p in student.request('state')['plans'] if p['id'] == plan['id'])
        progress = self.exercise(student, plan)
        trainer.request('plan', dict(plan, title='Título atualizado'))
        self.assertEqual(student.request('state')['workoutProgress'][0]['session'], progress['session'])
        changed = [dict(item) for item in plan['items']]
        changed[0]['reps'] = '15'
        trainer.request('plan', dict(plan, items=changed))
        self.assertEqual(student.request('state')['workoutProgress'], [])
        self.assert_error(student, 'workout/complete', {'plan': plan['id'], 'session': progress['session']}, 409)
        fresh = next(p for p in student.request('state')['plans'] if p['id'] == plan['id'])
        self.assertNotEqual(fresh['version'], plan['version'])

    def test_formatting_and_art_changes_preserve_progress(self):
        trainer, student, sid, plan, _ = self.training_fixture()
        progress = self.exercise(student, plan)
        edited = [dict(item, sets=str(item['sets']), load=str(item['load']), rest=str(item['rest']),
                       notes=item.get('notes', '')+'  ', illustration='auto') for item in plan['items']]
        trainer.request('plan', dict(plan, title='Somente formatação', items=edited))
        current = student.request('state')
        self.assertEqual(next(p for p in current['plans'] if p['id'] == plan['id'])['version'], plan['version'])
        self.assertEqual(current['workoutProgress'][0]['session'], progress['session'])

    def test_static_paths_and_route_alias(self):
        client = self.client()
        with client.opener.open(self.base, timeout=10) as response:
            self.assertIn('EvoFit', response.read().decode())
        for asset, expected_type in [('app.js', 'javascript'), ('workouts.js', 'javascript'),
                                     ('style.css', 'text/css'), ('images/extension.svg', 'image/svg+xml')]:
            with client.opener.open(self.base+asset, timeout=10) as response:
                self.assertEqual(response.status, 200)
                self.assertIn(expected_type, response.headers.get('Content-Type', ''))
        for path in ['server.py', '.env', '../.env', 'php/config.php', 'database/schema.sql', 'evofit.sqlite3',
                     'images/%2e%2e/%2e%2e/.env', 'images/%2e%2e/%2e%2e/server.py']:
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as caught:
                    client.opener.open(self.base+path, timeout=10)
                self.assertEqual(caught.exception.code, 404)
        client.login('aluno@evofit.demo', 'aluno')
        with client.opener.open(self.base+'api/state', timeout=10) as response:
            self.assertEqual(json.load(response)['user']['role'], 'aluno')


if __name__ == '__main__':
    if not os.environ.get('EVOFIT_TEST_URL'):
        raise SystemExit('Defina EVOFIT_TEST_URL para uma instância PHP/MySQL dedicada a testes.')
    unittest.main(verbosity=2)
