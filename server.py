"""Entrada compatível: Python inicia a aplicação PHP com banco MySQL."""
import sys
from tools.manage import main

if __name__ == '__main__':
    arguments = sys.argv[1:]
    if arguments and arguments[0] == '--init':
        arguments = ['init', *arguments[1:]]
    elif not arguments:
        arguments = ['serve']
    raise SystemExit(main(arguments))
