"""Inicia o EvoFit acadêmico com Docker, sem depender de PHP/MySQL no computador.

Exemplos: python tools/docker_academico.py iniciar --abrir
          python tools/docker_academico.py iniciar --testes
          python tools/docker_academico.py parar
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen

from preparar_academico import preparar
from abrir_index import abrir_index_pronto

ROOT = Path(__file__).resolve().parents[1]


def executar(argumentos):
    # Uma lista de argumentos evita interpolação de shell e preserva códigos de erro.
    subprocess.run(argumentos, cwd=ROOT, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('acao', choices=['iniciar', 'parar', 'validar'])
    parser.add_argument('--testes', action='store_true', help='Banco isolado; porta 4185')
    parser.add_argument('--rebuild', action='store_true', help='Reconstruir a imagem após alterar dependências')
    parser.add_argument('--abrir', action='store_true', help='Abrir index.html no navegador após a inicialização')
    args = parser.parse_args()
    preparar()
    projeto = 'evofit-academico-test' if args.testes else 'evofit-academico'
    compose = ['docker', 'compose', '--env-file', '.env.academico', '-p', projeto,
               '-f', 'compose.academico.yaml']
    if args.testes:
        compose += ['-f', 'infra/testes.academico.yaml']
    if args.acao == 'parar':
        executar(compose + ['stop'])  # Não apaga os volumes nem o banco.
        return 0
    if args.acao == 'validar':
        if not args.testes:
            parser.error('Use validar --testes: os testes gravam dados fictícios.')
        executar(compose + ['exec', '-T', 'app', 'python', '-m', 'unittest', 'discover',
                            '-s', 'tests', '-p', 'test_academico.py', '-v'])
        return 0
    imagem = subprocess.run(['docker', 'image', 'inspect', 'evofit-academico:dev'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if imagem.returncode or args.rebuild:
        build = ['docker', 'build', '-f', 'Dockerfile.academico', '-t', 'evofit-academico:dev']
        ca = os.environ.get('CODEX_PROXY_CERT')
        if ca and Path(ca).is_file():
            build += ['--secret', f'id=proxy_ca,src={ca}']
        executar(build + ['.'])
    executar(compose + ['up', '-d', '--wait', '--wait-timeout', '180', 'db'])
    executar(compose + ['up', '-d', '--no-build', 'app'])
    executar(compose + ['exec', '-T', 'app', 'python', 'app.py', 'init-db'])
    porta = 4185 if args.testes else 4173
    for tentativa in range(20):
        try:
            with urlopen(f'http://127.0.0.1:{porta}/api/saude', timeout=5) as resposta:
                assert resposta.status == 200
                json.load(resposta)
            with urlopen(f'http://127.0.0.1:{porta}/index.html', timeout=5) as resposta:
                assert 'EvoFit' in resposta.read().decode('utf-8')
            print(f'EvoFit acadêmico: banco e index.html verificados na porta {porta}.')
            if args.abrir:
                # O navegador pertence ao computador do usuário, não ao container.
                abrir_index_pronto(f'http://127.0.0.1:{porta}')
            return 0
        except (URLError, TimeoutError):
            if tentativa == 19:
                raise
            time.sleep(1)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as erro:
        raise SystemExit(erro.returncode)
