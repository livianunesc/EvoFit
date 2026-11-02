import os, json, sqlite3, hashlib, secrets, hmac, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from http.cookies import SimpleCookie
from pathlib import Path

ROOT=Path(__file__).parent
DB=os.environ.get('DATABASE_PATH',str(ROOT/'evofit.sqlite3'))
def connect():
    db=sqlite3.connect(DB); db.row_factory=sqlite3.Row; db.execute('PRAGMA foreign_keys=ON'); return db
def password(value,salt=None):
    salt=salt or secrets.token_hex(16)
    return salt+':'+hashlib.scrypt(value.encode(),salt=salt.encode(),n=16384,r=8,p=1).hex()
def valid_password(value,stored): return hmac.compare_digest(password(value,stored.split(':')[0]),stored)
def init():
    with connect() as d:
        d.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT UNIQUE NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL,trainer INTEGER REFERENCES users(id),goal TEXT DEFAULT '');
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user INTEGER REFERENCES users(id),expires REAL);
CREATE TABLE IF NOT EXISTS plans(id INTEGER PRIMARY KEY,student INTEGER REFERENCES users(id),kind TEXT,title TEXT,items TEXT);
CREATE TABLE IF NOT EXISTS logs(id INTEGER PRIMARY KEY,student INTEGER REFERENCES users(id),kind TEXT,data TEXT,date TEXT DEFAULT CURRENT_TIMESTAMP);''')
        if not d.execute('SELECT id FROM users LIMIT 1').fetchone():
            d.execute('INSERT INTO users VALUES(1,?,?,?,?,NULL,?)',('Livia · Personal','personal@evofit.demo',password('EvoFit123!'),'personal','Acompanhar cada conquista'))
            d.execute('INSERT INTO users VALUES(2,?,?,?,?,1,?)',('Ana Silva','aluno@evofit.demo',password('EvoFit123!'),'aluno','Ganhar força e qualidade de vida'))
            for title,items in [('Segunda · Inferiores',[dict(name='Agachamento',sets=3,reps='12',load=20,rest=60,notes='Mantenha a coluna neutra.'),dict(name='Leg press',sets=3,reps='15',load=60,rest=60,notes='Controle a descida.')]),('Quarta · Superiores',[dict(name='Remada',sets=3,reps='12',load=15,rest=60,notes='Aproxime as escápulas.')])]:
                d.execute('INSERT INTO plans(student,kind,title,items) VALUES(2,?,?,?)',('workout',title,json.dumps(items)))
            d.execute('INSERT INTO plans(student,kind,title,items) VALUES(2,?,?,?)',('diet','Plano equilibrado',json.dumps([dict(name='Café da manhã',time='07:00',food='Ovos, pão integral e banana',quantity='2 ovos, 2 fatias, 1 unidade'),dict(name='Almoço',time='12:30',food='Arroz, feijão, frango e salada',quantity='100 g, 80 g, 120 g, à vontade')])))
            for date,weight,waist in [('2026-09-01',72,82),('2026-10-01',71,80),('2026-11-01',70,78)]:
                d.execute('INSERT INTO logs(student,kind,data,date) VALUES(2,?,?,?)',('measurement',json.dumps(dict(weight=weight,waist=waist,hip=98,chest=90)),date))
            d.execute('INSERT INTO logs(student,kind,data) VALUES(2,?,?)',('workout',json.dumps(dict(title='Segunda · Inferiores',exercises=[dict(name='Agachamento',load=20,done=True)],notes='Boa disposição'))))
class Error(Exception):
    def __init__(self,message,status=400): self.message,self.status=message,status
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args): pass
    def send(self,obj,status=200,cookie=None):
        raw=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def do_GET(self):
        if self.path.startswith('/api/'):
            self.api(); return
        path=ROOT/'static'/('index.html' if self.path=='/' else self.path.lstrip('/').split('?')[0])
        if path not in [ROOT/'static'/x for x in ['index.html','app.js','style.css']]:self.send_error(404);return
        self.send_response(200);self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css'}[path.suffix[1:]]);self.end_headers();self.wfile.write(path.read_bytes())
    def do_POST(self): self.api()
    def api(self):
        try:
            if self.command=='POST':
                if self.headers.get('Sec-Fetch-Site')=='cross-site': raise Error('Origem não autorizada.',403)
                size=int(self.headers.get('Content-Length','0'))
                if size>100000: raise Error('Dados muito grandes.')
                try:b=json.loads(self.rfile.read(size))
                except Exception:raise Error('Dados inválidos.')
                if not isinstance(b,dict):raise Error('Dados inválidos.')
            else:b={}
            with connect() as d:
                route=self.path.split('?')[0]
                if route in ['/api/login','/api/register']:
                    email=str(b.get('email','')).strip().lower(); pw=str(b.get('password','')); role=b.get('role')
                    if '@' not in email or len(email)>200 or len(pw)<8 or role not in ['personal','aluno']:raise Error('Informe e-mail válido, perfil e senha com ao menos 8 caracteres.')
                    if route.endswith('register'):
                        name=str(b.get('name','')).strip()
                        if not name:raise Error('Informe seu nome.')
                        try:d.execute('INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)',(name,email,password(pw),role))
                        except sqlite3.IntegrityError:raise Error('Este e-mail já está cadastrado.')
                    u=d.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                    if not u or u['role']!=role or not valid_password(pw,u['password']):raise Error('E-mail, senha ou perfil incorretos.',401)
                    token=secrets.token_urlsafe(32);d.execute('INSERT INTO sessions VALUES(?,?,?)',(token,u['id'],time.time()+86400))
                    self.send({'ok':True},cookie='session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=86400'+('; Secure' if os.environ.get('SECURE_COOKIE')=='1' else ''));return
                c=SimpleCookie();c.load(self.headers.get('Cookie',''));token=c['session'].value if 'session' in c else ''
                u=d.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user WHERE s.token=? AND s.expires>?',(token,time.time())).fetchone()
                if not u:raise Error('Entre para continuar.',401)
                if route=='/api/logout':d.execute('DELETE FROM sessions WHERE token=?',(token,));self.send({'ok':True},cookie='session=; Path=/; Max-Age=0');return
                if route=='/api/state':
                    students=[dict(x) for x in d.execute('SELECT id,name,email,goal FROM users WHERE trainer=?',(u['id'],))] if u['role']=='personal' else [dict(id=u['id'],name=u['name'],email=u['email'],goal=u['goal'])]
                    ids=[x['id'] for x in students]; plans=[];logs=[]
                    for sid in ids:
                        plans += [dict(x,items=json.loads(x['items'])) for x in d.execute('SELECT * FROM plans WHERE student=?',(sid,))]
                        logs += [dict(x,data=json.loads(x['data'])) for x in d.execute('SELECT * FROM logs WHERE student=? ORDER BY date,id',(sid,))]
                    self.send(dict(user={k:u[k] for k in ['id','name','email','role','goal']},students=students,plans=plans,logs=logs));return
                if route=='/api/student':
                    if u['role']!='personal':raise Error('Acesso restrito ao personal.',403)
                    name=str(b.get('name','')).strip();email=str(b.get('email','')).strip().lower();pw=str(b.get('password',''))
                    if not name or '@' not in email or len(pw)<8:raise Error('Preencha nome, e-mail e senha com ao menos 8 caracteres.')
                    try:d.execute('INSERT INTO users(name,email,password,role,trainer,goal) VALUES(?,?,?,?,?,?)',(name,email,password(pw),'aluno',u['id'],str(b.get('goal',''))))
                    except sqlite3.IntegrityError:raise Error('E-mail já cadastrado. Use outro e-mail para o novo aluno.')
                elif route=='/api/profile':
                    name=str(b.get('name','')).strip()
                    if not name:raise Error('Informe seu nome.')
                    d.execute('UPDATE users SET name=?,goal=? WHERE id=?',(name,str(b.get('goal','')),u['id']))
                elif route in ['/api/plan','/api/log']:
                    sid=int(b.get('student',u['id']))
                    if u['role']=='aluno' and sid!=u['id'] or u['role']=='personal' and not d.execute('SELECT id FROM users WHERE id=? AND trainer=?',(sid,u['id'])).fetchone():raise Error('Acesso negado.',403)
                    if route=='/api/plan':
                        if u['role']!='personal':raise Error('Somente personal pode editar planos.',403)
                        kind=b.get('kind');title=str(b.get('title','')).strip();items=b.get('items')
                        if kind not in ['workout','diet'] or not title or not isinstance(items,list) or not items:raise Error('Preencha o título e ao menos um item.')
                        for item in items:
                            if not isinstance(item,dict) or not str(item.get('name','')).strip():raise Error('Informe o nome de cada item.')
                            if kind=='workout' and (float(item.get('sets',0))<=0 or float(item.get('load',0))<0 or float(item.get('rest',0))<0 or not item.get('reps')):raise Error('Confira séries, repetições, carga e descanso.')
                            if kind=='diet' and (not item.get('food') or not item.get('quantity') or not item.get('time')):raise Error('Preencha horário, alimentos e quantidades.')
                        if b.get('id'):
                            cur=d.execute('UPDATE plans SET title=?,items=? WHERE id=? AND student=? AND kind=?',(title,json.dumps(items),int(b['id']),sid,kind))
                            if not cur.rowcount:raise Error('Plano não encontrado.',404)
                        else:d.execute('INSERT INTO plans(student,kind,title,items) VALUES(?,?,?,?)',(sid,kind,title,json.dumps(items)))
                    else:
                        if u['role']!='aluno':raise Error('Somente aluno registra progresso.',403)
                        kind=b.get('kind');data=b.get('data',{})
                        if kind=='measurement':
                            for k in ['weight','waist','hip','chest']:
                                value=float(data.get(k,0))
                                if not 0<value<500:raise Error('Informe peso e medidas entre 0 e 500.')
                        elif kind=='workout':
                            p=d.execute('SELECT * FROM plans WHERE id=? AND student=? AND kind=?',(int(b.get('plan',0)),sid,'workout')).fetchone()
                            if not p:raise Error('Treino não encontrado.',404)
                            exercises=data.get('exercises',[]);expected=json.loads(p['items'])
                            if len(exercises)!=len(expected) or not all(isinstance(x,dict) and x.get('done') is True and 0<=float(x.get('load',-1))<2000 for x in exercises):raise Error('Marque todos os exercícios e informe as cargas para concluir.')
                            data['title']=p['title']
                            for x,y in zip(exercises,expected):x['name']=y['name']
                        else:raise Error('Registro inválido.')
                        d.execute('INSERT INTO logs(student,kind,data) VALUES(?,?,?)',(sid,kind,json.dumps(data)))
                else:raise Error('Página não encontrada.',404)
                self.send({'ok':True})
        except Error as e:self.send({'error':e.message},e.status)
        except (ValueError,TypeError,KeyError):self.send({'error':'Confira os campos informados.'},400)
        except Exception:self.send({'error':'Não foi possível concluir. Tente novamente.'},500)
if __name__=='__main__':
    init()
    if '--init' not in __import__('sys').argv:ThreadingHTTPServer(('0.0.0.0',int(os.environ.get('PORT','4173'))),Handler).serve_forever()
