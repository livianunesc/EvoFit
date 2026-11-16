"""Entrada Flask da versão acadêmica: HTTP -> modelos -> DAO -> MySQL.

Inicie com python app.py serve. O frontend raiz usa Fetch para estas rotas.
A antiga API PHP permanece separada para consulta e compatibilidade histórica.
"""
import argparse
from functools import wraps
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
from urllib.parse import urlsplit

from dotenv import dotenv_values
from flask import Flask, Response, g, jsonify, request, send_from_directory, session
import mysql.connector
from werkzeug.exceptions import HTTPException
from werkzeug.security import check_password_hash, generate_password_hash

from dao import BancoDados, ExercicioDAO, RegistroDAO, TreinoDAO, UsuarioDAO
from models import Aluno, ErroDominio, Exercicio, ItemTreino, Treino, texto

ROOT = Path(__file__).resolve().parent


def chave_sessao(diretorio):
    """Segredo local persistente: reiniciar o processo não derruba os logins."""
    diretorio.mkdir(parents=True, exist_ok=True)
    caminho = diretorio / 'session.key'
    try:
        # O_EXCL impede que dois processos sobrescrevam a chave um do outro.
        fd = os.open(caminho, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return caminho.read_text(encoding='ascii').strip()
    with os.fdopen(fd, 'w', encoding='ascii') as arquivo:
        chave = secrets.token_hex(32)
        arquivo.write(chave)
    return chave


def criar_config():
    # As variáveis injetadas têm precedência sobre o arquivo local ignorado pelo Git.
    local = dotenv_values(ROOT / '.env.academico')
    def valor(nome, padrao):
        return os.environ.get(nome, local.get(nome) or padrao)
    return dict(DB_HOST=valor('DB_HOST', '127.0.0.1'), DB_PORT=int(valor('DB_PORT', '3306')),
                DB_NAME=valor('DB_NAME', 'evofit_academico'), DB_USER=valor('DB_USER', 'root'),
                DB_PASSWORD=valor('DB_PASSWORD', ''),
                EVOFIT_STATE_DIR=valor('EVOFIT_STATE_DIR', str(ROOT / '.local' / 'evofit-academico')),
                SECRET_KEY=valor('FLASK_SECRET_KEY', ''), PHP_BIN=valor('PHP_BIN', ''),
                SESSION_COOKIE_SECURE=valor('SECURE_COOKIE', '0') == '1')


def create_app(config=None):
    app = Flask(__name__, static_folder=None)
    app.config.update(criar_config())
    if config:
        app.config.update(config)
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = chave_sessao(Path(app.config['EVOFIT_STATE_DIR']))
    app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE='Strict',
                      SESSION_COOKIE_NAME='evofit_academico', MAX_CONTENT_LENGTH=100_000)
    banco = BancoDados(dict(host=app.config['DB_HOST'], port=app.config['DB_PORT'],
                            database=app.config['DB_NAME'], user=app.config['DB_USER'],
                            password=app.config['DB_PASSWORD']))
    usuarios = UsuarioDAO(banco)
    exercicios = ExercicioDAO(banco)
    treinos = TreinoDAO(banco)
    registros = RegistroDAO(banco)
    app.extensions['evofit_banco'] = banco
    app.extensions['evofit_daos'] = dict(usuarios=usuarios, exercicios=exercicios,
                                       treinos=treinos, registros=registros)

    def autenticado(funcao):
        @wraps(funcao)
        def executar(*args, **kwargs):
            g.usuario = usuarios.por_id(session.get('usuario_id')) if session.get('usuario_id') else None
            if g.usuario is None:
                session.clear()
                raise ErroDominio('Entre para continuar.', 401)
            return funcao(*args, **kwargs)
        return executar

    def personal(funcao):
        @wraps(funcao)
        @autenticado
        def executar(*args, **kwargs):
            # Polimorfismo em uso: esta regra consulta o método da entidade carregada.
            if not g.usuario.pode_prescrever():
                raise ErroDominio('Esta operação é exclusiva do personal.', 403)
            return funcao(*args, **kwargs)
        return executar

    def corpo():
        if not request.is_json:
            raise ErroDominio('Envie os dados no formato JSON.', 415)
        resultado = request.get_json()
        if not isinstance(resultado, dict):
            raise ErroDominio('Envie um objeto JSON.')
        return resultado

    def senha_valida(senha):
        if not isinstance(senha, str) or not 8 <= len(senha) <= 128:
            raise ErroDominio('Use uma senha com 8 a 128 caracteres.')
        return senha

    def modelo_treino(dados):
        itens = dados.get('exercicios')
        if not isinstance(itens, list) or not all(isinstance(item, dict) for item in itens):
            raise ErroDominio('Informe a lista de exercícios do treino.')
        return Treino(dados.get('aluno_id'), dados.get('titulo'),
                      [ItemTreino(item.get('exercicio_id'), item.get('series'),
                                  item.get('repeticoes'), item.get('carga'), item.get('descanso'))
                       for item in itens])

    @app.before_request
    def verificar_origem():
        # Não há CORS permissivo: a própria aplicação serve HTML e API na mesma origem.
        if request.path.startswith('/api/') and request.method not in ('GET', 'HEAD', 'OPTIONS'):
            origem = request.headers.get('Origin')
            if request.headers.get('Sec-Fetch-Site') == 'cross-site':
                raise ErroDominio('Origem não autorizada.', 403)
            if origem and urlsplit(origem).netloc != request.host:
                raise ErroDominio('Origem não autorizada.', 403)

    @app.after_request
    def cabecalhos(resposta):
        resposta.headers['X-Content-Type-Options'] = 'nosniff'
        resposta.headers['Referrer-Policy'] = 'same-origin'
        if request.path.startswith('/api/') or request.path == '/relatorio-php':
            resposta.headers['Cache-Control'] = 'no-store'
        return resposta

    @app.errorhandler(ErroDominio)
    def erro_dominio(erro):
        return jsonify(erro=str(erro)), erro.status

    @app.errorhandler(HTTPException)
    def erro_http(erro):
        mensagens = {400: 'JSON inválido ou campos incorretos.', 404: 'Página não encontrada.',
                     405: 'Método HTTP não permitido.', 413: 'Dados muito grandes.'}
        return jsonify(erro=mensagens.get(erro.code, 'Não foi possível processar a solicitação.')), erro.code

    @app.errorhandler(mysql.connector.Error)
    def erro_mysql(erro):
        # Não devolva conexão, SQL nem credenciais em resposta ou log.
        if isinstance(erro, mysql.connector.IntegrityError):
            return jsonify(erro='O registro possui vínculos ou uma chave já utilizada.'), 409
        return jsonify(erro='Banco indisponível. Confira a configuração e inicialize o esquema.'), 503

    @app.get('/api/saude')
    def saude():
        banco.verificar()
        return jsonify(status='ok', banco='conectado')

    @app.post('/api/login')
    def login():
        dados = corpo()
        email = texto(dados.get('email'), 'E-mail', 200).lower()
        senha = dados.get('senha')
        if not isinstance(senha, str) or len(senha) > 128:
            raise ErroDominio('E-mail ou senha incorretos.', 401)
        linha = usuarios.por_email(email)
        if not linha or not check_password_hash(linha['senha_hash'], senha):
            raise ErroDominio('E-mail ou senha incorretos.', 401)
        session.clear()
        session['usuario_id'] = linha['id']
        return jsonify(usuario=usuarios.por_id(linha['id']).publico(), mensagem='Login realizado.')

    @app.post('/api/logout')
    def logout():
        session.clear()
        return jsonify(mensagem='Sessão encerrada.')

    @app.get('/api/sessao')
    @autenticado
    def sessao():
        return jsonify(usuario=g.usuario.publico())

    @app.route('/api/alunos', methods=['GET', 'POST'])
    @personal
    def alunos():
        if request.method == 'GET':
            return jsonify(alunos=usuarios.listar_alunos(g.usuario))
        dados = corpo()
        aluno = Aluno(dados.get('nome'), dados.get('email'), dados.get('objetivo', ''))
        id = usuarios.inserir_aluno(aluno, senha_valida(dados.get('senha')), g.usuario)
        return jsonify(id=id, mensagem='Aluno cadastrado.'), 201

    @app.route('/api/alunos/<int:id>', methods=['PUT', 'DELETE'])
    @personal
    def aluno(id):
        if request.method == 'DELETE':
            usuarios.remover_aluno(id, g.usuario)
            return jsonify(mensagem='Aluno excluído.')
        dados = corpo()
        entidade = Aluno(dados.get('nome'), dados.get('email'), dados.get('objetivo', ''))
        nova_senha = senha_valida(dados['senha']) if dados.get('senha') else None
        usuarios.atualizar_aluno(id, entidade, g.usuario, nova_senha)
        return jsonify(mensagem='Aluno atualizado.')

    @app.route('/api/exercicios', methods=['GET', 'POST'])
    @autenticado
    def catalogo():
        if request.method == 'GET':
            return jsonify(exercicios=exercicios.listar())
        if not g.usuario.pode_prescrever():
            raise ErroDominio('Somente o personal pode alterar o catálogo.', 403)
        dados = corpo()
        entidade = Exercicio(dados.get('nome'), dados.get('grupo_muscular'), dados.get('instrucoes', ''))
        return jsonify(id=exercicios.inserir(entidade), mensagem='Exercício cadastrado.'), 201

    @app.route('/api/exercicios/<int:id>', methods=['PUT', 'DELETE'])
    @personal
    def exercicio(id):
        if request.method == 'DELETE':
            exercicios.remover(id)
            return jsonify(mensagem='Exercício excluído.')
        dados = corpo()
        exercicios.atualizar(id, Exercicio(dados.get('nome'), dados.get('grupo_muscular'),
                                          dados.get('instrucoes', '')))
        return jsonify(mensagem='Exercício atualizado.')

    @app.route('/api/treinos', methods=['GET', 'POST'])
    @autenticado
    def lista_treinos():
        if request.method == 'GET':
            return jsonify(treinos=treinos.listar(g.usuario))
        if not g.usuario.pode_prescrever():
            raise ErroDominio('Somente o personal pode prescrever treinos.', 403)
        id = treinos.salvar(modelo_treino(corpo()), g.usuario)
        return jsonify(id=id, mensagem='Treino cadastrado.'), 201

    @app.route('/api/treinos/<int:id>', methods=['PUT', 'DELETE'])
    @personal
    def treino(id):
        if request.method == 'DELETE':
            treinos.remover(id, g.usuario)
            return jsonify(mensagem='Treino excluído.')
        treinos.salvar(modelo_treino(corpo()), g.usuario, id)
        return jsonify(mensagem='Treino atualizado.')

    @app.post('/api/treinos/<int:id>/concluir')
    @autenticado
    def concluir(id):
        if g.usuario.pode_prescrever():
            raise ErroDominio('Somente o aluno pode concluir seu treino.', 403)
        dados = corpo()
        registro_id, repetido = registros.concluir(id, g.usuario, dados.get('cargas'), dados.get('chave'), dados.get('versao'))
        return jsonify(registro_id=registro_id, repetido=repetido,
                       mensagem='Treino já registrado.' if repetido else 'Treino concluído.'), 200 if repetido else 201

    @app.get('/api/historico')
    @autenticado
    def historico():
        return jsonify(registros=registros.historico(g.usuario))

    @app.get('/api/ranking')
    @autenticado
    def ranking():
        return jsonify(ranking=registros.ranking(g.usuario))

    @app.get('/relatorio-php')
    @personal
    def relatorio_php():
        php = app.config.get('PHP_BIN') or shutil.which('php')
        if not php:
            raise ErroDominio('O relatório requer PHP CLI com PDO MySQL instalado.', 503)
        ambiente = dict(os.environ)
        for nome in ('DB_HOST', 'DB_PORT', 'DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            ambiente[nome] = str(app.config[nome])
        try:
            resultado = subprocess.run([php, str(ROOT / 'php_academico' / 'relatorio.php')],
                                       input=json.dumps({'personal_id': g.usuario.id}),
                                       text=True, capture_output=True, timeout=15, env=ambiente, check=False)
        except (OSError, subprocess.TimeoutExpired):
            raise ErroDominio('Não foi possível gerar o relatório PHP.', 503) from None
        if resultado.returncode != 0:
            raise ErroDominio('Relatório PHP indisponível. Confira PHP/PDO MySQL e o banco.', 503)
        resposta = Response(resultado.stdout, mimetype='text/html')
        resposta.headers['Content-Security-Policy'] = "default-src 'self'; style-src 'self' 'unsafe-inline'; base-uri 'self'; frame-ancestors 'none'"
        return resposta

    @app.get('/')
    @app.get('/index.html')
    def inicio():
        return send_from_directory(ROOT, 'index.html')

    @app.get('/<any(css,js):pasta>/<path:arquivo>')
    def recurso(pasta, arquivo):
        if not arquivo.endswith('.css' if pasta == 'css' else '.js'):
            raise ErroDominio('Arquivo não encontrado.', 404)
        return send_from_directory(ROOT / pasta, arquivo)

    @app.get('/static/<any(fonts,images):pasta>/<path:arquivo>')
    def visual(pasta, arquivo):
        # Reaproveita apenas fontes e imagens locais, sem expor a antiga entrada PHP.
        extensoes = ('.ttf', '.woff2', '.txt') if pasta == 'fonts' else ('.svg', '.png', '.jpg', '.webp')
        if not arquivo.endswith(extensoes):
            raise ErroDominio('Arquivo não encontrado.', 404)
        return send_from_directory(ROOT / 'static' / pasta, arquivo)

    @app.get('/pages/<path:arquivo>')
    def pagina(arquivo):
        if not arquivo.endswith('.html'):
            raise ErroDominio('Página não encontrada.', 404)
        return send_from_directory(ROOT / 'pages', arquivo)

    @app.get('/apresentacao/')
    @app.get('/apresentacao/<path:arquivo>')
    def apresentacao(arquivo='index.html'):
        if not arquivo.endswith(('.html', '.css', '.js')):
            raise ErroDominio('Arquivo não encontrado.', 404)
        return send_from_directory(ROOT / 'apresentacao', arquivo)

    return app


def seed_demo(banco):
    """Adiciona demonstração apenas num banco vazio; nunca substitui dados reais."""
    with banco.transacao() as conexao:
        with conexao.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM usuarios')
            if cursor.fetchone()[0]:
                return False
            senha = generate_password_hash('EvoFit123!')
            cursor.execute('INSERT INTO usuarios(nome,email,senha_hash,papel,personal_id,objetivo) '
                           'VALUES(%s,%s,%s,%s,NULL,%s)',
                           ('Livia Personal', 'personal@evofit.demo', senha, 'personal', 'Acompanhar a equipe'))
            personal_id = cursor.lastrowid
            cursor.execute('INSERT INTO usuarios(nome,email,senha_hash,papel,personal_id,objetivo) '
                           'VALUES(%s,%s,%s,%s,%s,%s)',
                           ('Ana Atleta', 'aluno@evofit.demo', senha, 'aluno', personal_id, 'Ganhar força'))
            aluno_id = cursor.lastrowid
            cursor.execute('INSERT INTO usuarios(nome,email,senha_hash,papel,personal_id,objetivo) '
                           'VALUES(%s,%s,%s,%s,%s,%s)',
                           ('Aluno iniciante', 'iniciante@evofit.demo', senha, 'aluno', personal_id, 'Começar a treinar'))
            exemplos = [('Agachamento', 'Pernas', 'Mantenha a coluna neutra e desça de forma controlada.'),
                        ('Remada', 'Costas', 'Puxe os cotovelos para trás sem curvar a coluna.'),
                        ('Supino', 'Peitoral', 'Use uma carga adequada e movimento controlado.'),
                        ('Prancha', 'Core', 'Mantenha o tronco alinhado e respire normalmente.')]
            ids = []
            for nome, grupo, instrucoes in exemplos:
                cursor.execute('INSERT INTO exercicios(nome,grupo_muscular,instrucoes) VALUES(%s,%s,%s)',
                               (nome, grupo, instrucoes))
                ids.append(cursor.lastrowid)
            treino_ids = []
            for titulo, itens in [('Treino A — Força', [(ids[0], 20), (ids[1], 15)]),
                                  ('Treino B — Condicionamento', [(ids[2], 12)])]:
                cursor.execute('INSERT INTO treinos(aluno_id,titulo) VALUES(%s,%s)', (aluno_id, titulo))
                treino_id = cursor.lastrowid
                treino_ids.append(treino_id)
                for ordem, (exercicio_id, carga) in enumerate(itens):
                    cursor.execute('INSERT INTO treino_exercicios(treino_id,exercicio_id,ordem,series,'
                                   'repeticoes,carga,descanso) VALUES(%s,%s,%s,%s,%s,%s,%s)',
                                   (treino_id, exercicio_id, ordem, 3, '12', carga, 60))
            for indice, total in enumerate((35, 37)):
                cursor.execute('INSERT INTO registros(treino_id,concluido_em,carga_total,chave) '
                               'VALUES(%s,UTC_TIMESTAMP(),%s,%s)',
                               (treino_ids[0], total, f'seed-demo-{indice + 1}'))
            return True


def main(argumentos=None):
    parser = argparse.ArgumentParser(description='EvoFit acadêmico: Flask/POO/DAO + MySQL')
    comandos = parser.add_subparsers(dest='comando', required=True)
    iniciar = comandos.add_parser('init-db', help='Criar tabelas e demonstração em banco novo')
    iniciar.add_argument('--schema', type=Path, default=ROOT / 'banco' / 'schema.sql')
    iniciar.add_argument('--create-database', action='store_true')
    iniciar.add_argument('--no-seed', action='store_true')
    servir = comandos.add_parser('serve', help='Iniciar o servidor local de desenvolvimento')
    servir.add_argument('--host', default='127.0.0.1')
    servir.add_argument('--port', type=int, default=4173)
    args = parser.parse_args(argumentos)
    app = create_app()
    if args.comando == 'init-db':
        try:
            banco = app.extensions['evofit_banco']
            banco.inicializar(args.schema, args.create_database)
            if not args.no_seed:
                seed_demo(banco)
            print('Banco acadêmico pronto; registros existentes foram preservados.')
        except (mysql.connector.Error, OSError):
            parser.exit(1, 'Não foi possível preparar o banco. Confira DB_*, serviço MySQL e schema.\n')
    else:
        # debug=False evita debugger remoto e recarga que duplicaria processos.
        app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()
