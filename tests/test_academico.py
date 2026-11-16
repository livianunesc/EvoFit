"""Testes do contrato Flask e das entidades: não substituem MySQL por mocks.

Modelos rodam sempre. A integração exige EVOFIT_ACADEMICO_TEST_DB apontando para
um banco exclusivo terminado em _test ou _teste, com schema já criado.
Os testes inserem dados com e-mails únicos e não apagam registros existentes.
"""
from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import sys
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from models import Aluno, ErroDominio, Exercicio, ItemTreino, Personal, Treino, Usuario


class Entidades(unittest.TestCase):
    def test_encapsulamento_heranca_e_polimorfismo(self):
        personal = Personal('  Livia  ', 'LIVIA@example.com')
        aluno = Aluno('Ana', 'ana@example.com', 'Força')
        self.assertEqual(personal.nome, 'Livia')
        self.assertEqual(personal.email, 'livia@example.com')
        self.assertEqual([u.pode_prescrever() for u in (personal, aluno)], [True, False])
        self.assertNotIn('senha_hash', aluno.publico())
        with self.assertRaises(ErroDominio):
            aluno.nome = ' '
        with self.assertRaises(ErroDominio):
            aluno.email = 'invalido'
        with self.assertRaises(TypeError):
            Usuario('Abstrato', 'abc@example.com')

    def test_composicao_e_validacao_de_prescricao(self):
        item = ItemTreino(1, 3, '12', 20.5, 60)
        treino = Treino(2, 'Treino A', [item])
        self.assertIs(treino.exercicios[0], item)
        for campo in (True, -1, float('inf'), float('nan'), '1.005'):
            with self.subTest(carga=campo), self.assertRaises(ErroDominio):
                ItemTreino(1, 3, '12', campo, 60)
        with self.assertRaises(ErroDominio):
            Treino(2, 'Treino vazio', [])
        with self.assertRaises(ErroDominio):
            Treino(2, 'Duplicado', [item, item])
        with self.assertRaises(ErroDominio):
            Exercicio('Agachamento', '', '')


@unittest.skipUnless(os.environ.get('EVOFIT_ACADEMICO_TEST_DB'),
                     'Integração não executada: configure um MySQL exclusivo em EVOFIT_ACADEMICO_TEST_DB.')
class IntegracaoMySQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import create_app
        from werkzeug.security import generate_password_hash
        db_name = os.environ['EVOFIT_ACADEMICO_TEST_DB']
        if not db_name.endswith(('_test', '_teste')):
            raise RuntimeError('O banco de integração precisa terminar em _test ou _teste.')
        cls.app = create_app(dict(TESTING=True, DB_NAME=db_name,
                                  SECRET_KEY='chave-exclusiva-de-testes-sem-uso-real'))
        cls.banco = cls.app.extensions['evofit_banco']
        cls.banco.verificar()
        cls.senha = 'Teste123!'
        cls.personal_email = f'personal-{uuid.uuid4().hex}@example.com'
        cls.outro_email = f'outro-{uuid.uuid4().hex}@example.com'
        cls.independente_email = f'independente-{uuid.uuid4().hex}@example.com'
        with cls.banco.transacao() as conexao:
            with conexao.cursor() as cursor:
                ids = []
                for email, papel in ((cls.personal_email, 'personal'), (cls.outro_email, 'personal'),
                                     (cls.independente_email, 'aluno')):
                    cursor.execute('INSERT INTO usuarios(nome,email,senha_hash,papel,personal_id,objetivo) '
                                   'VALUES(%s,%s,%s,%s,NULL,%s)',
                                   ('Conta de teste', email, generate_password_hash(cls.senha), papel, 'Teste isolado'))
                    ids.append(cursor.lastrowid)
                cls.personal_id, cls.outro_id, cls.independente_id = ids

    def cliente(self, email=None):
        cliente = self.app.test_client()
        if email:
            resposta = cliente.post('/api/login', json=dict(email=email, senha=self.senha))
            self.assertEqual(resposta.status_code, 200, resposta.json)
        return cliente

    def criar_aluno(self, personal=None):
        personal = personal or self.cliente(self.personal_email)
        email = f'aluno-{uuid.uuid4().hex}@example.com'
        resposta = personal.post('/api/alunos', json=dict(nome='Ana de teste', email=email,
                                                        senha=self.senha, objetivo='Ganhar força'))
        self.assertEqual(resposta.status_code, 201, resposta.json)
        return resposta.json['id'], email

    def criar_exercicio(self, personal):
        resposta = personal.post('/api/exercicios', json=dict(nome='Remada de teste',
                                                            grupo_muscular='Costas', instrucoes='Controle o movimento.'))
        self.assertEqual(resposta.status_code, 201, resposta.json)
        return resposta.json['id']

    def fixture_treino(self):
        personal = self.cliente(self.personal_email)
        aluno_id, email = self.criar_aluno(personal)
        exercicio_id = self.criar_exercicio(personal)
        dados = dict(aluno_id=aluno_id, titulo='Treino de teste',
                     exercicios=[dict(exercicio_id=exercicio_id, series=3, repeticoes='12', carga=20.5, descanso=60)])
        resposta = personal.post('/api/treinos', json=dados)
        self.assertEqual(resposta.status_code, 201, resposta.json)
        aluno = self.cliente(email)
        dados['versao'] = next(t for t in aluno.get('/api/treinos').json['treinos'] if t['id'] == resposta.json['id'])['versao']
        return personal, aluno, resposta.json['id'], dados, email

    def test_autenticacao_validacao_e_protecao_de_arquivos(self):
        anonimo = self.cliente()
        self.assertEqual(anonimo.get('/api/sessao').status_code, 401)
        for rota in ('/.env.academico', '/app.py', '/dao.py', '/banco/schema.sql', '/css/../../.env.academico'):
            self.assertEqual(anonimo.get(rota).status_code, 404)
        self.assertEqual(anonimo.post('/api/login', json=dict(email="x' OR 1=1 --", senha='invalida')).status_code, 401)
        self.assertEqual(anonimo.post('/api/login', data='nao e JSON').status_code, 415)
        cliente = self.cliente(self.personal_email)
        self.assertNotIn('senha_hash', cliente.get('/api/sessao').json['usuario'])
        cookie = cliente.get_cookie('evofit_academico')
        self.assertTrue(cookie.http_only)
        self.assertEqual(cookie.same_site, 'Strict')
        self.assertEqual(cliente.post('/api/alunos', json={}, headers={'Origin': 'https://outro.example'}).status_code, 403)
        self.assertEqual(cliente.post('/api/logout', json={}).status_code, 200)
        self.assertEqual(cliente.get('/api/sessao').status_code, 401)
        self.assertEqual(anonimo.get('/api/saude').json['status'], 'ok')

    def test_crud_aluno_e_email_unico(self):
        personal = self.cliente(self.personal_email)
        id, email = self.criar_aluno(personal)
        dados = dict(nome='Ana atualizada', email=email, objetivo='Consistência')
        self.assertEqual(personal.put(f'/api/alunos/{id}', json=dados).status_code, 200)
        linha = next(u for u in personal.get('/api/alunos').json['alunos'] if u['id'] == id)
        self.assertEqual(linha['nome'], 'Ana atualizada')
        resposta = personal.post('/api/alunos', json={**dados, 'senha': self.senha})
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(personal.delete(f'/api/alunos/{id}').status_code, 200)
        self.assertEqual(personal.delete(f'/api/alunos/{id}').status_code, 404)
        self.assertEqual(self.cliente().post('/api/login', json=dict(email=email, senha=self.senha)).status_code, 401)

    def test_crud_exercicio_e_treino_com_integridade(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        exercicio_id = dados['exercicios'][0]['exercicio_id']
        self.assertEqual(personal.put(f'/api/exercicios/{exercicio_id}', json=dict(
            nome='Remada corrigida', grupo_muscular='Costas', instrucoes='Cotovelos para trás.')).status_code, 200)
        self.assertEqual(personal.put(f'/api/treinos/{id}', json={**dados, 'titulo': 'Treino revisado'}).status_code, 200)
        treino = next(t for t in aluno.get('/api/treinos').json['treinos'] if t['id'] == id)
        self.assertEqual(treino['titulo'], 'Treino revisado')
        self.assertEqual(treino['exercicios'][0]['nome'], 'Remada corrigida')
        self.assertEqual(personal.delete(f'/api/exercicios/{exercicio_id}').status_code, 409)
        self.assertEqual(personal.delete(f'/api/alunos/{dados["aluno_id"]}').status_code, 409)
        self.assertEqual(personal.delete(f'/api/treinos/{id}').status_code, 200)
        self.assertEqual(personal.delete(f'/api/exercicios/{exercicio_id}').status_code, 200)
        self.assertFalse(any(t['id'] == id for t in aluno.get('/api/treinos').json['treinos']))

    def test_edicao_com_fk_invalida_faz_rollback(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        itens = dados['exercicios'] + [{**dados['exercicios'][0], 'exercicio_id': 999_999_999}]
        resposta = personal.put(f'/api/treinos/{id}', json={**dados, 'titulo': 'Nao deve persistir', 'exercicios': itens})
        self.assertEqual(resposta.status_code, 409)
        depois = next(t for t in aluno.get('/api/treinos').json['treinos'] if t['id'] == id)
        self.assertEqual(depois['titulo'], dados['titulo'])
        self.assertEqual(len(depois['exercicios']), 1)

    def test_autorizacao_isolamento_equipe_e_papel(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        outro = self.cliente(self.outro_email)
        independente = self.cliente(self.independente_email)
        self.assertEqual(aluno.get('/api/alunos').status_code, 403)
        self.assertEqual(aluno.post('/api/exercicios', json={}).status_code, 403)
        self.assertEqual(aluno.post('/api/treinos', json=dados).status_code, 403)
        self.assertEqual(personal.post(f'/api/treinos/{id}/concluir', json={}).status_code, 403)
        self.assertEqual(outro.put(f'/api/treinos/{id}', json=dados).status_code, 404)
        self.assertEqual(outro.delete(f'/api/treinos/{id}').status_code, 404)
        self.assertEqual(outro.delete(f'/api/alunos/{dados["aluno_id"]}').status_code, 404)
        self.assertEqual(independente.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[10], chave=str(uuid.uuid4()))).status_code, 404)
        self.assertFalse(any(t['id'] == id for t in outro.get('/api/treinos').json['treinos']))
        self.assertFalse(any(u['aluno_id'] == dados['aluno_id'] for u in outro.get('/api/ranking').json['ranking']))
        self.assertEqual(independente.get('/api/ranking').json['ranking'], [])

    def test_conclusao_idempotente_historico_e_ranking(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        chave = str(uuid.uuid4())
        self.assertEqual(aluno.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[], chave=chave, versao=dados['versao'])).status_code, 400)
        self.assertEqual(aluno.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[-2], chave=chave, versao=dados['versao'])).status_code, 400)
        primeira = aluno.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[25.5], chave=chave, versao=dados['versao']))
        repetida = aluno.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[25.5], chave=chave, versao=dados['versao']))
        self.assertEqual(primeira.status_code, 201, primeira.json)
        self.assertEqual(repetida.status_code, 200, repetida.json)
        self.assertEqual(primeira.json['registro_id'], repetida.json['registro_id'])
        self.assertTrue(repetida.json['repetido'])
        historico = aluno.get('/api/historico').json['registros']
        self.assertEqual(len(historico), 1)
        self.assertEqual(historico[0]['carga_total'], 25.5)
        self.assertTrue(historico[0]['concluido_em'].endswith('Z'))
        ranking = aluno.get('/api/ranking').json['ranking']
        atleta = next(u for u in ranking if u['aluno_id'] == dados['aluno_id'])
        self.assertEqual(atleta['total'], 1)
        self.assertNotIn('email', atleta)
        self.assertEqual(personal.delete(f'/api/treinos/{id}').status_code, 409)
        outro_aluno, _ = self.criar_aluno(personal)
        self.assertEqual(personal.put(f'/api/treinos/{id}', json={**dados, 'aluno_id': outro_aluno}).status_code, 409)

    def test_transferencia_preserva_autor_do_historico(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        novo_id, novo_email = self.criar_aluno(personal)
        resposta = personal.put(f'/api/treinos/{id}', json={**dados, 'aluno_id': novo_id})
        self.assertEqual(resposta.status_code, 200, resposta.json)
        self.assertFalse(any(t['id'] == id for t in aluno.get('/api/treinos').json['treinos']))
        novo = self.cliente(novo_email)
        self.assertTrue(any(t['id'] == id for t in novo.get('/api/treinos').json['treinos']))
        self.assertEqual(novo.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[20], chave=str(uuid.uuid4()), versao=dados['versao'])).status_code, 201)
        resposta = personal.put(f'/api/treinos/{id}', json=dados)
        self.assertEqual(resposta.status_code, 409)
        self.assertEqual(novo.get('/api/historico').json['registros'][0]['aluno_id'], novo_id)

    def test_ficha_obsoleta_rejeitada_e_reenvio_concluido_preservado(self):
        personal, aluno, id, dados, _ = self.fixture_treino()
        chave = str(uuid.uuid4())
        payload = dict(cargas=[20], chave=chave, versao=dados['versao'])
        itens = [{**dados['exercicios'][0], 'series': 4}]
        self.assertEqual(personal.put(f'/api/treinos/{id}', json={**dados, 'exercicios': itens}).status_code, 200)
        obsoleta = aluno.post(f'/api/treinos/{id}/concluir', json=payload)
        self.assertEqual(obsoleta.status_code, 409, obsoleta.json)
        self.assertEqual(aluno.get('/api/historico').json['registros'], [])
        atual = next(t for t in aluno.get('/api/treinos').json['treinos'] if t['id'] == id)
        self.assertNotEqual(atual['versao'], dados['versao'])
        payload['versao'] = atual['versao']
        primeira = aluno.post(f'/api/treinos/{id}/concluir', json=payload)
        self.assertEqual(primeira.status_code, 201, primeira.json)
        self.assertEqual(personal.put(f'/api/treinos/{id}', json=dados).status_code, 200)
        repetida = aluno.post(f'/api/treinos/{id}/concluir', json=payload)
        self.assertEqual(repetida.status_code, 200, repetida.json)
        self.assertTrue(repetida.json['repetido'])
        self.assertEqual(len(aluno.get('/api/historico').json['registros']), 1)

    def test_finalizacao_simultanea_nao_duplica(self):
        _, aluno, id, dados, email = self.fixture_treino()
        clientes = [self.cliente(email), self.cliente(email)]
        chave = str(uuid.uuid4())
        def finalizar(cliente):
            return cliente.post(f'/api/treinos/{id}/concluir', json=dict(cargas=[15], chave=chave, versao=dados['versao']))
        with ThreadPoolExecutor(max_workers=2) as executor:
            respostas = list(executor.map(finalizar, clientes))
        self.assertEqual(sorted(r.status_code for r in respostas), [200, 201])
        self.assertEqual(len(aluno.get('/api/historico').json['registros']), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
