"""Entrada principal da entrega: servidor Python/Flask com MySQL.

Use ``python server.py --abrir`` para iniciar e abrir index.html automaticamente.
Sem --abrir, o servidor executa sem abrir o navegador. A edição PHP anterior continua
preservada e pode ser iniciada separadamente com ``python server.py --legacy-php``.
"""
import sys


def main():
    if '--legacy-php' in sys.argv[1:]:
        # Compatibilidade explícita; não confunde a API PHP com a entrega Flask.
        from tools.manage import main as iniciar_php
        argumentos = [arg for arg in sys.argv[1:] if arg != '--legacy-php']
        return iniciar_php(argumentos or ['serve'])
    from app import main as iniciar_flask
    return iniciar_flask(['serve', *sys.argv[1:]])


if __name__ == '__main__':
    raise SystemExit(main())
