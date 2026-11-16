"""DAOs: somente esta camada consulta e grava os dados do sistema acadêmico.

Todos os valores usam placeholders %s. A conexão fecha em finally; gravações
compostas usam uma transação, para confirmar tudo ou desfazer tudo com rollback.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import re
import uuid

import mysql.connector
from mysql.connector import IntegrityError
from werkzeug.security import generate_password_hash

from models import Aluno, Exercicio, ErroDominio, Treino, numero, usuario_do_banco


def publico(linha):
    """Converte tipos do MySQL para JSON previsível, sem devolver hashes."""
    if linha is None:
        return None
    saida = {}
    for chave, valor in linha.items():
        if chave == 'senha_hash':
            continue
        if isinstance(valor, Decimal):
            valor = float(valor)
        elif isinstance(valor, datetime):
            # O banco guarda UTC; Z permite ao navegador converter para o fuso local.
            valor = valor.replace(tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')
        saida[chave] = valor
    return saida


def versao_prescricao(itens):
    """A versão muda se um item prescrito muda, mesmo com igual quantidade de itens.

    Nome/título não entram no hash: são rótulos; a identidade do exercício entra.
    Carga usa duas casas para que Decimal do MySQL e float do JSON sejam iguais.
    """
    linhas = [dict(exercicio_id=item['exercicio_id'], ordem=item['ordem'],
                   series=item['series'], repeticoes=item['repeticoes'],
                   carga=format(Decimal(str(item['carga'])), '.2f'), descanso=item['descanso'])
              for item in itens]
    dados = json.dumps(linhas, sort_keys=True, ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(dados.encode('utf-8')).hexdigest()


class BancoDados:
    def __init__(self, config):
        self.config = {chave: config[chave] for chave in ('host', 'port', 'user', 'password', 'database')}
        if not re.fullmatch(r'[A-Za-z0-9_]+', self.config['database']):
            raise ValueError('DB_NAME deve conter somente letras, números e sublinhado.')

    def conectar(self, selecionar=True):
        config = dict(self.config)
        if not selecionar:
            config.pop('database')
        return mysql.connector.connect(**config, charset='utf8mb4', connection_timeout=10,
                                       autocommit=False, use_pure=True, time_zone='+00:00')

    @contextmanager
    def transacao(self, selecionar=True):
        conexao = self.conectar(selecionar)
        try:
            yield conexao
            conexao.commit()
        except Exception:
            conexao.rollback()
            raise
        finally:
            conexao.close()

    def verificar(self):
        with self.transacao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute('SELECT 1')
                return cursor.fetchone()[0] == 1

    def inicializar(self, caminho, criar=False):
        if criar:
            # O identificador não pode usar %s: a expressão regular do construtor o valida.
            with self.transacao(False) as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute(f'CREATE DATABASE IF NOT EXISTS `{self.config["database"]}` '
                                   'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
        sql = caminho.read_text(encoding='utf-8')
        # O schema contém DDL simples, sem procedures, DELIMITER nem ; em literais.
        sql = '\n'.join(linha for linha in sql.splitlines() if not linha.lstrip().startswith('--'))
        with self.transacao() as conexao:
            with conexao.cursor() as cursor:
                for comando in sql.split(';'):
                    if comando.strip():
                        cursor.execute(comando)


class UsuarioDAO:
    def __init__(self, banco):
        self.banco = banco

    def por_email(self, email):
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT * FROM usuarios WHERE email=%s', (email,))
                return cursor.fetchone()

    def por_id(self, id):
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT * FROM usuarios WHERE id=%s', (id,))
                linha = cursor.fetchone()
                return usuario_do_banco(linha) if linha else None

    def listar_alunos(self, personal):
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT id,nome,email,objetivo,personal_id,papel FROM usuarios "
                               "WHERE personal_id=%s AND papel='aluno' ORDER BY nome,id", (personal.id,))
                return [publico(linha) for linha in cursor.fetchall()]

    def inserir_aluno(self, aluno, senha, personal):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute('INSERT INTO usuarios(nome,email,senha_hash,papel,personal_id,objetivo) '
                                   'VALUES(%s,%s,%s,%s,%s,%s)',
                                   (aluno.nome, aluno.email, generate_password_hash(senha), 'aluno',
                                    personal.id, aluno.objetivo))
                    return cursor.lastrowid
        except IntegrityError:
            raise ErroDominio('Este e-mail já está cadastrado.', 409) from None

    def atualizar_aluno(self, id, aluno, personal, senha=None):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor(dictionary=True) as cursor:
                    cursor.execute("SELECT id FROM usuarios WHERE id=%s AND personal_id=%s "
                                   "AND papel='aluno' FOR UPDATE", (id, personal.id))
                    if cursor.fetchone() is None:
                        raise ErroDominio('Aluno não encontrado na sua equipe.', 404)
                    cursor.execute('UPDATE usuarios SET nome=%s,email=%s,objetivo=%s WHERE id=%s',
                                   (aluno.nome, aluno.email, aluno.objetivo, id))
                    if senha is not None:
                        cursor.execute('UPDATE usuarios SET senha_hash=%s WHERE id=%s',
                                       (generate_password_hash(senha), id))
        except IntegrityError:
            raise ErroDominio('Este e-mail já está cadastrado.', 409) from None

    def remover_aluno(self, id, personal):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute("DELETE FROM usuarios WHERE id=%s AND personal_id=%s AND papel='aluno'",
                                   (id, personal.id))
                    if cursor.rowcount == 0:
                        raise ErroDominio('Aluno não encontrado na sua equipe.', 404)
        except IntegrityError:
            raise ErroDominio('Este aluno possui treinos ou histórico. Preserve esses vínculos.', 409) from None


class ExercicioDAO:
    """O catálogo é compartilhado; somente contas personal podem modificá-lo."""
    def __init__(self, banco):
        self.banco = banco

    def listar(self):
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT id,nome,grupo_muscular,instrucoes FROM exercicios ORDER BY nome,id')
                return [publico(linha) for linha in cursor.fetchall()]

    def inserir(self, exercicio):
        with self.banco.transacao() as conexao:
            with conexao.cursor() as cursor:
                cursor.execute('INSERT INTO exercicios(nome,grupo_muscular,instrucoes) VALUES(%s,%s,%s)',
                               (exercicio.nome, exercicio.grupo_muscular, exercicio.instrucoes))
                return cursor.lastrowid

    def atualizar(self, id, exercicio):
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT id FROM exercicios WHERE id=%s FOR UPDATE', (id,))
                if cursor.fetchone() is None:
                    raise ErroDominio('Exercício não encontrado.', 404)
                cursor.execute('UPDATE exercicios SET nome=%s,grupo_muscular=%s,instrucoes=%s WHERE id=%s',
                               (exercicio.nome, exercicio.grupo_muscular, exercicio.instrucoes, id))

    def remover(self, id):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute('DELETE FROM exercicios WHERE id=%s', (id,))
                    if cursor.rowcount == 0:
                        raise ErroDominio('Exercício não encontrado.', 404)
        except IntegrityError:
            raise ErroDominio('Exercício utilizado em um treino. Remova o vínculo antes de excluí-lo.', 409) from None


class TreinoDAO:
    def __init__(self, banco):
        self.banco = banco

    @staticmethod
    def _escopo(usuario, alias='u'):
        if usuario.pode_prescrever():
            return f'{alias}.personal_id=%s', (usuario.id,)
        return f'{alias}.id=%s', (usuario.id,)

    def listar(self, usuario):
        filtro, parametros = self._escopo(usuario)
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT t.id,t.aluno_id,t.titulo,u.nome AS aluno_nome FROM treinos t '
                               f'JOIN usuarios u ON u.id=t.aluno_id WHERE {filtro} ORDER BY t.id', parametros)
                treinos = [publico(linha) for linha in cursor.fetchall()]
                for treino in treinos:
                    cursor.execute('SELECT te.exercicio_id,te.ordem,te.series,te.repeticoes,te.carga,te.descanso,'
                                   'e.nome,e.grupo_muscular,e.instrucoes FROM treino_exercicios te '
                                   'JOIN exercicios e ON e.id=te.exercicio_id '
                                   'WHERE te.treino_id=%s ORDER BY te.ordem,te.id', (treino['id'],))
                    treino['exercicios'] = [publico(linha) for linha in cursor.fetchall()]
                    treino['versao'] = versao_prescricao(treino['exercicios'])
                return treinos

    def salvar(self, treino, personal, id=None):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor(dictionary=True) as cursor:
                    # A autorização pertence ao servidor: não confiamos no aluno_id do formulário.
                    cursor.execute("SELECT id FROM usuarios WHERE id=%s AND personal_id=%s "
                                   "AND papel='aluno' FOR UPDATE", (treino.aluno_id, personal.id))
                    if cursor.fetchone() is None:
                        raise ErroDominio('Aluno não encontrado na sua equipe.', 404)
                    if id is not None:
                        cursor.execute('SELECT t.id FROM treinos t JOIN usuarios u ON u.id=t.aluno_id '
                                       'WHERE t.id=%s AND u.personal_id=%s FOR UPDATE', (id, personal.id))
                        if cursor.fetchone() is None:
                            raise ErroDominio('Treino não encontrado na sua equipe.', 404)
                        # Um histórico não pode ser transferido para outro aluno por uma edição.
                        cursor.execute('SELECT aluno_id FROM treinos WHERE id=%s', (id,))
                        anterior = cursor.fetchone()
                        if anterior['aluno_id'] != treino.aluno_id:
                            cursor.execute('SELECT COUNT(*) AS total FROM registros WHERE treino_id=%s', (id,))
                            if cursor.fetchone()['total']:
                                raise ErroDominio('Treino com histórico não pode ser transferido para outro aluno.', 409)
                        cursor.execute('UPDATE treinos SET titulo=%s,aluno_id=%s WHERE id=%s',
                                       (treino.titulo, treino.aluno_id, id))
                        cursor.execute('DELETE FROM treino_exercicios WHERE treino_id=%s', (id,))
                    else:
                        cursor.execute('INSERT INTO treinos(aluno_id,titulo) VALUES(%s,%s)',
                                       (treino.aluno_id, treino.titulo))
                        id = cursor.lastrowid
                    for ordem, item in enumerate(treino.exercicios):
                        cursor.execute('INSERT INTO treino_exercicios(treino_id,exercicio_id,ordem,series,'
                                       'repeticoes,carga,descanso) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                                       (id, item.exercicio_id, ordem, item.series, item.repeticoes,
                                        item.carga, item.descanso))
                    return id
        except IntegrityError:
            raise ErroDominio('Confira se todos os exercícios selecionados existem.', 409) from None

    def remover(self, id, personal):
        try:
            with self.banco.transacao() as conexao:
                with conexao.cursor() as cursor:
                    cursor.execute('DELETE t FROM treinos t JOIN usuarios u ON u.id=t.aluno_id '
                                   'WHERE t.id=%s AND u.personal_id=%s', (id, personal.id))
                    if cursor.rowcount == 0:
                        raise ErroDominio('Treino não encontrado na sua equipe.', 404)
        except IntegrityError:
            raise ErroDominio('Este treino possui histórico. Sua exclusão não é permitida.', 409) from None


class RegistroDAO:
    def __init__(self, banco):
        self.banco = banco

    def concluir(self, id, aluno, cargas, chave, versao):
        if not isinstance(chave, str):
            raise ErroDominio('Informe uma chave UUID para esta conclusão.')
        try:
            chave = str(uuid.UUID(chave))
        except (ValueError, AttributeError):
            raise ErroDominio('A chave de conclusão precisa ser um UUID válido.') from None
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                # Bloquear o treino serializa duas finalizações simultâneas do mesmo aluno.
                cursor.execute('SELECT id FROM treinos WHERE id=%s AND aluno_id=%s FOR UPDATE', (id, aluno.id))
                if cursor.fetchone() is None:
                    raise ErroDominio('Treino não encontrado para sua conta.', 404)
                cursor.execute('SELECT id,treino_id FROM registros WHERE chave=%s', (chave,))
                anterior = cursor.fetchone()
                if anterior:
                    if anterior['treino_id'] != id:
                        raise ErroDominio('Chave já utilizada em outra conclusão.', 409)
                    return anterior['id'], True
                cursor.execute('SELECT exercicio_id,ordem,series,repeticoes,carga,descanso FROM treino_exercicios '
                               'WHERE treino_id=%s ORDER BY ordem,id', (id,))
                itens = cursor.fetchall()
                if not isinstance(versao, str) or versao != versao_prescricao(itens):
                    raise ErroDominio('O treino foi atualizado. Recarregue a ficha antes de concluir.', 409)
                if not isinstance(cargas, list) or not itens or len(cargas) != len(itens):
                    raise ErroDominio('Informe uma carga para cada exercício do treino.')
                total = sum((numero(carga, 'Carga', 0, 1999) for carga in cargas), Decimal(0))
                # carga_total é a soma das cargas, não séries × repetições × carga.
                cursor.execute('INSERT INTO registros(treino_id,concluido_em,carga_total,chave) '
                               'VALUES(%s,UTC_TIMESTAMP(),%s,%s)', (id, total, chave))
                return cursor.lastrowid, False

    def historico(self, usuario):
        filtro, parametros = TreinoDAO._escopo(usuario)
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                cursor.execute('SELECT r.id,r.treino_id,t.aluno_id,r.concluido_em,r.carga_total,'
                               't.titulo,u.nome AS aluno_nome FROM registros r '
                               'JOIN treinos t ON t.id=r.treino_id JOIN usuarios u ON u.id=t.aluno_id '
                               f'WHERE {filtro} ORDER BY r.concluido_em DESC,r.id DESC', parametros)
                return [publico(linha) for linha in cursor.fetchall()]

    def ranking(self, usuario):
        personal_id = usuario.id if usuario.pode_prescrever() else usuario.personal_id
        if personal_id is None:
            return []
        with self.banco.transacao() as conexao:
            with conexao.cursor(dictionary=True) as cursor:
                # LEFT JOIN mantém no ranking o aluno que ainda não concluiu um treino.
                cursor.execute("SELECT u.id AS aluno_id,u.nome,COUNT(r.id) AS total FROM usuarios u "
                               "LEFT JOIN treinos t ON t.aluno_id=u.id LEFT JOIN registros r ON r.treino_id=t.id WHERE u.personal_id=%s "
                               "AND u.papel='aluno' GROUP BY u.id,u.nome ORDER BY total DESC,u.nome,u.id",
                               (personal_id,))
                ranking = [publico(linha) for linha in cursor.fetchall()]
                posicao, anterior = 0, None
                for linha in ranking:
                    if linha['total'] != anterior:
                        posicao += 1  # Empates compartilham posição; ranking denso.
                        anterior = linha['total']
                    linha['posicao'] = posicao
                return ranking
