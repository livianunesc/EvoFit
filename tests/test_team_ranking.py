"""Team ranking integration: use a dedicated instance via EVOFIT_TEST_URL.

Optional EVOFIT_TEST_PHP points to a PHP executable/wrapper connected to that same
isolated database, enabling UTC boundary fixtures and deterministic calendar tests.
Tests create unique accounts and do not remove or alter existing user records.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest
import urllib.error
import urllib.parse
import urllib.request
import uuid

from test_php_flow import ApiClient

ROOT=Path(__file__).resolve().parents[1]


def query(client, route='ranking', **params):
    url=client.base+'api.php?'+urllib.parse.urlencode({'route':route,**params},doseq=True)
    with client.opener.open(urllib.request.Request(url),timeout=20) as response:
        return json.load(response)


class TeamRanking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=os.environ.get('EVOFIT_TEST_URL')
        if not cls.base:
            raise unittest.SkipTest('EVOFIT_TEST_URL is required; team ranking API checks were not run.')

    def team(self, names=('Aluno A','Aluno B','Aluno C')):
        token=uuid.uuid4().hex
        trainer=ApiClient(self.base)
        trainer.request('register',dict(name='Personal '+token,email=token+'@example.com',password='Teste123!',role='personal'))
        users=[]
        for index,name in enumerate(names):
            email=f'team-{token}-{index}@example.com'
            trainer.request('student',dict(name=name,email=email,password='Teste123!',goal='Objetivo privado'))
            student=ApiClient(self.base);student.login(email,'aluno','Teste123!')
            state=student.request('state');sid=state['user']['id']
            items=[dict(name='Cadeira extensora',sets=3,reps='12',load=15,rest=60,notes='Orientação privada')]
            trainer.request('plan',dict(student=sid,kind='workout',title='Treino privado',items=items))
            plan=next(p for p in student.request('state')['plans'] if p['kind']=='workout')
            users.append(dict(client=student,id=sid,email=email,plan=plan,name=name))
        return trainer,users

    def complete(self, user, repeat=False):
        client=user['client'];plan=user['plan']
        progress=client.request('exercise',dict(plan=plan['id'],version=plan['version'],index=0,load=17.5,done=True))['progress']
        payload=dict(plan=plan['id'],session=progress['session'],notes='Treino concluído')
        result=client.request('workout/complete',payload)
        if repeat:
            again=client.request('workout/complete',payload)
            self.assertEqual(again['log'],result['log'])
            self.assertTrue(again['alreadyCompleted'])
        return result

    def test_team_scope_dense_ties_and_minimal_public_data(self):
        trainer,users=self.team()
        outsider,foreign=self.team(('Fora da equipe',))
        for user in users[:2]:
            self.complete(user);self.complete(user)
        for _ in range(3):self.complete(foreign[0])
        ranking=query(users[0]['client'])
        self.assertEqual(ranking['period'],'month')
        self.assertEqual(ranking['trainer'],{k:trainer.request('state')['user'][k] for k in ['id','name']})
        self.assertEqual(ranking['title'],'TEAM '+ranking['trainer']['name']+' FOCUS')
        self.assertEqual([x['student'] for x in ranking['members']],[x['id'] for x in users])
        self.assertEqual([x['completed'] for x in ranking['members']],[2,2,0])
        self.assertEqual([x['position'] for x in ranking['members']],[1,1,2])
        self.assertEqual([x['isCurrent'] for x in ranking['members']],[True,False,False])
        self.assertEqual(ranking['totalCompleted'],4)
        for member in ranking['members']:
            self.assertEqual(set(member),{'student','name','completed','position','isCurrent'})
        personal=query(trainer)
        self.assertEqual([x['isCurrent'] for x in personal['members']],[False,False,False])
        state=users[0]['client'].request('state')
        self.assertEqual(state['teamRanking'],ranking)
        self.assertEqual([s['id'] for s in state['students']],[users[0]['id']])
        self.assertTrue(all(p['student']==users[0]['id'] for p in state['plans']))
        self.assertTrue(all(log['student']==users[0]['id'] for log in state['logs']))
        # Another trainer's query parameter never selects their team or exposes their records.
        foreign_id=outsider.request('state')['user']['id']
        self.assertEqual(query(users[0]['client'],trainer=foreign_id),ranking)
        self.assertEqual(query(trainer,trainer=foreign_id),personal)

    def test_partial_exercises_and_measurements_do_not_score_duplicate_finish_once(self):
        trainer,users=self.team(('Concluindo treino','Aguardando treino'))
        user=users[0];client=user['client'];plan=user['plan']
        client.request('log',dict(kind='measurement',data=dict(weight=70,waist=80,hip=90,chest=95)))
        progress=client.request('exercise',dict(plan=plan['id'],version=plan['version'],index=0,load=20,done=True))['progress']
        self.assertEqual(query(client)['totalCompleted'],0)
        payload=dict(plan=plan['id'],session=progress['session'])
        first=client.request('workout/complete',payload)
        second=client.request('workout/complete',payload)
        self.assertEqual(first['log'],second['log'])
        ranking=query(client)
        self.assertEqual(ranking['totalCompleted'],1)
        self.assertEqual([x['completed'] for x in ranking['members']],[1,0])
        self.assertEqual(query(trainer)['totalCompleted'],1)
        self.assertEqual(query(client,period='all')['totalCompleted'],1)
        self.assertEqual(query(client,'state',period='all')['teamRanking']['period'],'all')

    def test_independent_student_and_read_only_authenticated_routes(self):
        client=ApiClient(self.base);token=uuid.uuid4().hex
        client.request('register',dict(name='Aluno independente',email=token+'@example.com',password='Teste123!',role='aluno'))
        ranking=query(client,trainer=1)
        self.assertIsNone(ranking['trainer']);self.assertEqual(ranking['members'],[])
        self.assertEqual(ranking['totalCompleted'],0)
        self.assertEqual(ranking['title'],'Equipe ainda não vinculada')
        self.assertEqual(client.request('state')['teamRanking'],ranking)
        with self.assertRaises(urllib.error.HTTPError) as error:query(ApiClient(self.base))
        self.assertEqual(error.exception.code,401)
        with self.assertRaises(urllib.error.HTTPError) as error:client.request('ranking',{})
        self.assertEqual(error.exception.code,405)
        with self.assertRaises(urllib.error.HTTPError) as error:query(client,period='another-team')
        self.assertEqual(error.exception.code,400)
        with self.assertRaises(urllib.error.HTTPError) as error:
            client.opener.open(client.base+'api.php?route=ranking&period[]=all')
        self.assertEqual(error.exception.code,400)
        # CLI development route preserves the same authenticated team contract.
        with client.opener.open(client.base+'api/ranking?period=all') as response:
            self.assertEqual(json.load(response)['period'],'all')

    def test_current_month_uses_utc_bounds_in_the_configured_timezone(self):
        php=os.environ.get('EVOFIT_TEST_PHP')
        if not php:raise unittest.SkipTest('EVOFIT_TEST_PHP required for safe database boundary fixtures.')
        trainer,users=self.team(('Aluno limite de mês',))
        user=users[0]
        script=r'''require "php/bootstrap.php"; require "php/ranking.php";
        $input=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
        $db=evo_db();$student=evo_query($db,"SELECT id,email FROM users WHERE email=? AND role='aluno'",[$input['email']])->fetch();
        if(!$student || (int)$student['id']!==$input['student']) throw new RuntimeException('Test database mismatch; no fixture written.');
        $window=evo_ranking_window();$utc=new DateTimeZone('UTC');
        $start=new DateTimeImmutable($window['start'],$utc);$end=new DateTimeImmutable($window['end'],$utc);
        $dates=[$start->modify('-1 second'),$start,$end->modify('-1 second'),$end];
        $db->beginTransaction();
        try {foreach($dates as $date)evo_query($db,"INSERT INTO logs(student,kind,data,date) VALUES(?,'workout',?,?)",[$input['student'],evo_json(['title'=>'Fixture de limite UTC','exercises'=>[['name'=>'Teste','load'=>10,'done'=>true]],'notes'=>'']),$date->format('Y-m-d H:i:s')]);$db->commit();}
        catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}
        echo evo_json($window);'''
        result=subprocess.run([php,'-r',script],cwd=ROOT,input=json.dumps(dict(student=user['id'],email=user['email'])),text=True,capture_output=True,check=True,timeout=30)
        window=json.loads(result.stdout)
        monthly=query(user['client']);all_time=query(user['client'],period='all')
        self.assertEqual(monthly['month'],window['month'])
        self.assertEqual(monthly['totalCompleted'],2)
        self.assertEqual(all_time['totalCompleted'],4)


    def test_migrated_date_only_rows_use_midnight_utc_at_calendar_edges(self):
        php=os.environ.get('EVOFIT_TEST_PHP')
        if not php:raise unittest.SkipTest('EVOFIT_TEST_PHP required for safe migrated-date fixtures.')
        _,users=self.team(('Aluno datas migradas',))
        user=users[0]
        script=r'''require "php/bootstrap.php"; require "php/ranking.php";
        $input=json_decode(stream_get_contents(STDIN),true,512,JSON_THROW_ON_ERROR);
        $db=evo_db();$student=evo_query($db,"SELECT * FROM users WHERE email=? AND role='aluno'",[$input['email']])->fetch();
        if(!$student || (int)$student['id']!==$input['student']) throw new RuntimeException('Test database mismatch; no fixture written.');
        putenv('APP_TIMEZONE=UTC');$window=evo_ranking_window();$utc=new DateTimeZone('UTC');
        $start=new DateTimeImmutable($window['start'],$utc);$end=new DateTimeImmutable($window['end'],$utc);
        $dates=[$start->modify('-1 day'),$start,$end->modify('-1 day'),$end];
        $db->beginTransaction();
        try {foreach($dates as $date)evo_query($db,"INSERT INTO logs(student,kind,data,date) VALUES(?,'workout',?,?)",[$input['student'],evo_json(['title'=>'Fixture data migrada','exercises'=>[['name'=>'Teste','load'=>10,'done'=>true]],'notes'=>'']),$date->format('Y-m-d')]);$db->commit();}
        catch(Throwable $e){if($db->inTransaction())$db->rollBack();throw $e;}
        echo evo_json(['month'=>evo_team_ranking($db,$student,'month'),'all'=>evo_team_ranking($db,$student,'all')]);'''
        result=subprocess.run([php,'-r',script],cwd=ROOT,input=json.dumps(dict(student=user['id'],email=user['email'])),text=True,capture_output=True,check=True,timeout=30)
        rankings=json.loads(result.stdout)
        self.assertEqual(rankings['month']['totalCompleted'],2)
        self.assertEqual(rankings['all']['totalCompleted'],4)


class RankingCalendar(unittest.TestCase):
    def test_calendar_edges_and_daylight_saving_boundaries(self):
        php=os.environ.get('EVOFIT_TEST_PHP') or shutil.which('php')
        if not php:raise unittest.SkipTest('PHP executable required for deterministic timezone helper checks.')
        script=r'''require "php/bootstrap.php"; require "php/ranking.php";
        echo evo_json([
            evo_ranking_window(new DateTimeImmutable('2026-11-01T02:30:00Z'),new DateTimeZone('America/Sao_Paulo')),
            evo_ranking_window(new DateTimeImmutable('2026-11-15T12:00:00Z'),new DateTimeZone('America/New_York'))
        ]);'''
        result=subprocess.run([php,'-r',script],cwd=ROOT,text=True,capture_output=True,check=True,timeout=30)
        windows=json.loads(result.stdout)
        self.assertEqual(windows[0],dict(month='2026-10',start='2026-10-01 03:00:00',end='2026-11-01 03:00:00'))
        self.assertEqual(windows[1],dict(month='2026-11',start='2026-11-01 04:00:00',end='2026-12-01 05:00:00'))


if __name__=='__main__':unittest.main(verbosity=2)
