import unittest, tempfile, os, sys, threading, urllib.request, urllib.error, http.cookiejar, json, sqlite3
sys.path.insert(0,os.path.dirname(os.path.dirname(__file__)))
import server

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
if __name__=='__main__':unittest.main()
