import unittest, tempfile, os, sys, threading, urllib.request, urllib.error, http.cookiejar, json, sqlite3
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
from legacy import server_sqlite as server

class Flow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();server.DB=cls.tmp.name+'/test.sqlite3';server.init()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)+'/api/'
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
    @classmethod
    def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();cls.tmp.cleanup()
    def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def call(self,c,path,data=None):
        req=urllib.request.Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json'})
        with c.open(req) as r:return json.load(r)
    def login(self,c,email,role,pw='EvoFit123!'):return self.call(c,'login',dict(email=email,password=pw,role=role))
    def test_complete_flow_and_access(self):
        trainer=self.client();student=self.client();outsider=self.client()
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(trainer,'state')
        self.assertEqual(err.exception.code,401)
        self.login(trainer,'personal@evofit.demo','personal')
        self.call(trainer,'student',dict(name='Teste Integração',email='teste@example.com',password='Teste123!',goal='Força'))
        s=self.call(trainer,'state')['students'][-1]['id']
        items=[dict(name='Agachamento',sets=3,reps='12',load=20,rest=60,notes='Controle')]
        self.call(trainer,'plan',dict(student=s,kind='workout',title='Segunda · Pernas',items=items))
        self.call(trainer,'plan',dict(student=s,kind='diet',title='Plano diário',items=[dict(name='Almoço',time='12:00',food='Frango',quantity='120 g')]))
        self.login(student,'teste@example.com','aluno','Teste123!');st=self.call(student,'state')
        self.assertEqual(len(st['students']),1);self.assertEqual(len(st['plans']),2)
        workout=next(p for p in st['plans'] if p['kind']=='workout')
        self.call(trainer,'plan',dict(workout,title='Terça · Pernas'))
        self.assertEqual(self.call(student,'state')['plans'][0]['title'],'Terça · Pernas')
        with self.assertRaises(urllib.error.HTTPError):self.call(student,'log',dict(kind='workout',plan=workout['id'],data={'exercises':[]}))
        self.call(student,'log',dict(kind='workout',plan=workout['id'],data=dict(exercises=[dict(name='Agachamento',load=25,done=True)],notes='Concluído')))
        self.call(student,'log',dict(kind='measurement',data=dict(weight=70,waist=80,hip=95,chest=90)))
        updated=self.call(trainer,'state');logs=[l for l in updated['logs'] if l['student']==s]
        self.assertEqual(len(logs),2);self.assertEqual(logs[0]['data']['exercises'][0]['load'],25)
        self.call(student,'profile',dict(name='Nome atualizado',goal='Resistência'))
        self.assertEqual(self.call(trainer,'state')['students'][-1]['name'],'Nome atualizado')
        self.login(outsider,'aluno@evofit.demo','aluno')
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(outsider,'log',dict(student=s,kind='measurement',data={}))
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError):self.call(student,'plan',dict(workout,title='Alteração indevida'))
        other=self.client();self.call(other,'register',dict(name='Outro personal',email='outro@example.com',password='Teste123!',role='personal'))
        self.assertEqual(self.call(other,'state')['students'],[])
        with self.assertRaises(urllib.error.HTTPError):self.call(other,'plan',dict(workout,title='Indevido'))
        with sqlite3.connect(server.DB) as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM logs WHERE student=?',(s,)).fetchone()[0],2)
        self.call(student,'logout',{})
        with self.assertRaises(urllib.error.HTTPError):self.call(student,'state')
    def test_invalid_auth_and_duplicate(self):
        c=self.client()
        with self.assertRaises(urllib.error.HTTPError):self.login(c,'aluno@evofit.demo','personal')
        with self.assertRaises(urllib.error.HTTPError):self.login(c,'aluno@evofit.demo','aluno','errada123')
        with self.assertRaises(urllib.error.HTTPError):self.call(c,'register',dict(name='X',email='aluno@evofit.demo',password='Teste123!',role='aluno'))
    def progress_setup(self):
        trainer=self.client();student=self.client()
        self.login(trainer,'personal@evofit.demo','personal')
        email=self._testMethodName+'@example.com'
        self.call(trainer,'student',dict(name='Aluno de treino',email=email,password='Teste123!'))
        sid=next(x['id'] for x in self.call(trainer,'state')['students'] if x['email']==email)
        items=[dict(name='Cadeira extensora',sets=3,reps='12',load=15,rest=60,notes='Controle o movimento.'),dict(name='Agachamento',sets=3,reps='10',load=20,rest=90,notes='')]
        self.call(trainer,'plan',dict(student=sid,kind='workout',title='Quadríceps',items=items))
        self.login(student,email,'aluno','Teste123!')
        plan=self.call(student,'state')['plans'][0]
        return trainer,student,sid,plan,email
    def test_persistent_exercise_completion_and_idempotent_finish(self):
        trainer,student,sid,plan,email=self.progress_setup()
        pid=plan['id']
        progress=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=17.5,done=True))['progress']
        session=progress['session']
        self.assertEqual(progress['exercises'],[dict(load=17.5,done=True),dict(load=20,done=False)])
        resumed=self.client();self.login(resumed,email,'aluno','Teste123!')
        self.assertEqual(self.call(resumed,'state')['workoutProgress'][0],progress)
        # Idempotent initialization retains existing users, plans, logs and active sessions.
        server.init()
        self.assertEqual(self.call(resumed,'state')['workoutProgress'][0]['session'],session)
        visible=next(x for x in self.call(trainer,'state')['workoutProgress'] if x['student']==sid)
        self.assertEqual(visible['exercises'][0]['load'],17.5)
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'workout/complete',dict(plan=pid,version=plan['version'],session=session))
        self.assertEqual(err.exception.code,400)
        self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=18,done=False,session=session))
        self.assertFalse(self.call(student,'state')['workoutProgress'][0]['exercises'][0]['done'])
        self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=18,done=True,session=session))
        self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=1,load=25,done=True,session=session))
        # Simultaneous clicks/retries create one history entry.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(lambda client:self.call(client,'workout/complete',dict(plan=pid,version=plan['version'],session=session,notes='Treino completo')), [student,resumed]))
        self.assertEqual(responses[0]['log'],responses[1]['log'])
        self.assertEqual(sorted(x['alreadyCompleted'] for x in responses),[False,True])
        result=self.call(student,'state');self.assertEqual(result['workoutProgress'],[])
        self.assertEqual(len(result['logs']),1)
        self.assertEqual(result['logs'][0]['data']['exercises'],[dict(name='Cadeira extensora',load=18,done=True),dict(name='Agachamento',load=25,done=True)])
        self.assertEqual(result['logs'][0]['data']['notes'],'Treino completo')
        self.assertEqual(len([x for x in self.call(trainer,'state')['logs'] if x['student']==sid]),1)
        next_run=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=20,done=True))['progress']
        self.assertNotEqual(next_run['session'],session)
        self.assertFalse(next_run['exercises'][1]['done'])
    def test_exercise_validation_and_permissions(self):
        trainer,student,sid,plan,email=self.progress_setup();pid=plan['id']
        for payload in [dict(plan=pid,version=plan['version'],index=-1,load=20,done=True),dict(plan=pid,version=plan['version'],index=2,load=20,done=True),dict(plan=pid,version=plan['version'],index=True,load=20,done=True),dict(plan=pid,version=plan['version'],index=0,load=float('nan'),done=True),dict(plan=pid,version=plan['version'],index=0,load=float('inf'),done=True),dict(plan=pid,version=plan['version'],index=0,load=-1,done=True),dict(plan=pid,version=plan['version'],index=0,load=2000,done=True),dict(plan=pid,version=plan['version'],index=0,load=True,done=True),dict(plan=pid,version=plan['version'],index=0,load=20,done='true')]:
            with self.subTest(payload=payload):
                with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'exercise',payload)
                self.assertEqual(err.exception.code,400)
        self.assertEqual(self.call(student,'state')['workoutProgress'],[])
        outsider=self.client();self.login(outsider,'aluno@evofit.demo','aluno')
        for client in [outsider,trainer]:
            with self.assertRaises(urllib.error.HTTPError) as err:self.call(client,'exercise',dict(plan=pid,version=plan['version'],index=0,load=20,done=True))
            self.assertIn(err.exception.code,[403,404])
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'exercise',dict(student=2,plan=pid,version=plan['version'],index=0,load=20,done=True))
        self.assertEqual(err.exception.code,403)
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'exercise')
        self.assertEqual(err.exception.code,405)
        progress=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=20,done=True))['progress']
        for client in [outsider,trainer]:
            with self.assertRaises(urllib.error.HTTPError):self.call(client,'workout/complete',dict(plan=pid,version=plan['version'],session=progress['session']))
    def test_plan_edit_invalidates_unfinished_session(self):
        trainer,student,sid,plan,email=self.progress_setup();pid=plan['id']
        progress=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=25,done=True))['progress']
        # Renaming a workout preserves progress, changing exercise instructions invalidates it.
        self.call(trainer,'plan',dict(plan,title='Treino renomeado'))
        self.assertEqual(self.call(student,'state')['workoutProgress'][0]['session'],progress['session'])
        changed=[dict(x) for x in plan['items']];changed[0]['reps']='15'
        self.call(trainer,'plan',dict(plan,title='Treino atualizado',items=changed))
        self.assertEqual(self.call(student,'state')['workoutProgress'],[])
        plan=self.call(student,'state')['plans'][0]
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=1,load=20,done=True,session=progress['session']))
        self.assertEqual(err.exception.code,409)
        with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'workout/complete',dict(plan=pid,version=plan['version'],session=progress['session']))
        self.assertEqual(err.exception.code,409)
        fresh=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=30,done=True))['progress']
        self.assertNotEqual(fresh['session'],progress['session'])
        self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=1,load=25,done=True,session=fresh['session']))
        self.call(student,'workout/complete',dict(plan=pid,version=plan['version'],session=fresh['session']))
        changed[0]['load']=40
        self.call(trainer,'plan',dict(plan,title='Plano futuro',items=changed))
        self.assertEqual(self.call(student,'state')['logs'][0]['data']['exercises'][0]['load'],30)
    def test_stale_first_click_is_rejected_before_creating_progress(self):
        trainer,student,sid,plan,email=self.progress_setup();pid=plan['id']
        old_version=plan['version']
        self.assertEqual(len(old_version),64)
        changed=[dict(x) for x in plan['items']];changed.reverse()
        self.call(trainer,'plan',dict(plan,items=changed))
        for payload in [dict(plan=pid,version=old_version,index=0,load=25,done=True),dict(plan=pid,index=0,load=25,done=True)]:
            with self.assertRaises(urllib.error.HTTPError) as err:self.call(student,'exercise',payload)
            self.assertEqual(err.exception.code,409)
        updated=self.call(student,'state')
        self.assertEqual(updated['workoutProgress'],[])
        self.assertNotEqual(updated['plans'][0]['version'],old_version)
        self.call(student,'exercise',dict(plan=pid,version=updated['plans'][0]['version'],index=0,load=25,done=True))
        self.assertEqual(self.call(student,'state')['workoutProgress'][0]['exercises'][0]['load'],25)
    def test_editor_formatting_and_image_changes_preserve_progress(self):
        trainer,student,sid,plan,email=self.progress_setup();pid=plan['id']
        # Also covers pre-upgrade runs whose snapshot still contains raw seeded items.
        progress=self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=0,load=25,done=True))['progress']
        with sqlite3.connect(server.DB) as d:d.execute('UPDATE workout_runs SET snapshot=? WHERE session=?',(json.dumps(plan['items']),progress['session']))
        edited=[]
        for item in plan['items']:
            entry={k:str(v) for k,v in item.items()}
            entry.update(illustration='auto',sets='3.0',notes=entry.get('notes','')+'  ')
            edited.append(entry)
        self.call(trainer,'plan',dict(plan,title='Título atualizado pelo editor',items=edited))
        current=self.call(student,'state')
        self.assertEqual(current['plans'][0]['version'],plan['version'])
        self.assertEqual(current['workoutProgress'][0]['session'],progress['session'])
        self.call(student,'exercise',dict(plan=pid,version=plan['version'],index=1,load=30,done=True,session=progress['session']))
        self.call(student,'workout/complete',dict(plan=pid,session=progress['session']))
        self.assertEqual(len(self.call(student,'state')['logs']),1)
    def test_static_files_do_not_expose_source_or_database(self):
        client=self.client();base=self.base.removesuffix('api/')
        for path in ['server.py','../server.py','images/../server.py','images/%2e%2e/%2e%2e/server.py','evofit.sqlite3']:
            with self.subTest(path=path):
                with self.assertRaises(urllib.error.HTTPError) as err:client.open(base+path)
                self.assertEqual(err.exception.code,404)

if __name__=='__main__':unittest.main()
