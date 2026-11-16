"""Cria apenas a configuração local ignorada; nunca sobrescreve senhas existentes."""
from pathlib import Path
import secrets
import argparse

ROOT = Path(__file__).resolve().parents[1]


def preparar(local=False):
    destino = ROOT / '.env.academico'
    if destino.exists():
        print('Configuração local existente preservada: .env.academico')
        return
    # A senha é aleatória, exclusiva deste ambiente e nunca aparece no terminal.
    with destino.open('x', encoding='utf-8') as arquivo:
        if local:
            arquivo.write((ROOT / '.env.academico.example').read_text(encoding='utf-8'))
        else:
            arquivo.write('ACADEMIC_DB_PASSWORD=' + secrets.token_hex(24) + '\n')
    destino.chmod(0o600)
    print('Configuração local criada: .env.academico (não publicar no Git).')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', action='store_true', help='Usar MySQL local, sem Docker')
    preparar(local=parser.parse_args().local)
