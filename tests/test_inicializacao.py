"""Inicialização automática: testa HTTP real sem abrir navegador nem usar MySQL.

Execute: python -m unittest discover -s tests -p test_inicializacao.py -v
Somente webbrowser.open é substituído: saúde, HTML, espera e timeout usam
um servidor HTTP local, isolado, com porta escolhida pelo sistema operacional.
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import unittest
from unittest import mock
from urllib.request import urlopen
import webbrowser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.abrir_index import abrir_index_pronto


class EstadoServidor:
    """Eventos deixam o teste controlar quando cada pré-requisito fica pronto."""

    def __init__(self):
        self.saude_pronta = threading.Event()
        self.index_pronto = threading.Event()
        self.recebeu_saude = threading.Event()
        self.recebeu_index = threading.Event()
        self.status_saude = 'ok'
        self.titulo = 'EvoFit · Seu foco em movimento'


def criar_handler(estado):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, formato, *argumentos):
            # Não polui a saída do unittest com os acessos esperados de polling.
            pass

        def do_GET(self):
            if self.path == '/api/saude':
                estado.recebeu_saude.set()
                codigo = 200 if estado.saude_pronta.is_set() else 503
                corpo = json.dumps({'status': estado.status_saude}).encode()
                tipo = 'application/json'
            elif self.path == '/index.html':
                estado.recebeu_index.set()
                codigo = 200 if estado.index_pronto.is_set() else 503
                corpo = (
                    '<!doctype html><html lang="pt-BR"><head>'
                    f'<title>{estado.titulo}</title></head>'
                    '<body>EvoFit: página de entrada.</body></html>'
                ).encode()
                tipo = 'text/html; charset=utf-8'
            else:
                codigo, corpo, tipo = 404, b'Nao encontrado', 'text/plain'
            self.send_response(codigo)
            self.send_header('Content-Type', tipo)
            self.send_header('Content-Length', str(len(corpo)))
            self.end_headers()
            self.wfile.write(corpo)

    return Handler


class InicializacaoIndex(unittest.TestCase):
    def setUp(self):
        self.estado = EstadoServidor()
        self.servidor = ThreadingHTTPServer(
            ('127.0.0.1', 0), criar_handler(self.estado)
        )
        self.servidor.daemon_threads = True
        self.url = f'http://127.0.0.1:{self.servidor.server_port}'
        self.thread = threading.Thread(
            target=lambda: self.servidor.serve_forever(poll_interval=0.02),
            daemon=True,
        )
        self.thread.start()
        self.parado = False

    def tearDown(self):
        if not self.parado:
            self.servidor.shutdown()
            self.servidor.server_close()
        self.thread.join(timeout=2)

    def deixar_pronto(self):
        self.estado.saude_pronta.set()
        self.estado.index_pronto.set()

    def assert_indisponivel(self):
        """Nenhuma abertura ocorre quando a prontidão não foi demonstrada."""
        with mock.patch('tools.abrir_index.webbrowser.open') as abrir:
            self.assertFalse(abrir_index_pronto(
                self.url, timeout=0.25, intervalo=0.02
            ))
            abrir.assert_not_called()

    def test_aguarda_saude_e_index_antes_de_abrir_url_exata(self):
        resultado = []
        erros = []

        def iniciar():
            try:
                resultado.append(abrir_index_pronto(
                    self.url + '/', timeout=4, intervalo=0.02
                ))
            except BaseException as erro:
                erros.append(erro)

        with mock.patch('tools.abrir_index.webbrowser.open', return_value=True) as abrir:
            tarefa = threading.Thread(target=iniciar, daemon=True)
            tarefa.start()
            try:
                self.assertTrue(self.estado.recebeu_saude.wait(2))
                abrir.assert_not_called()
                self.estado.saude_pronta.set()
                self.assertTrue(self.estado.recebeu_index.wait(2))
                # Um banco saudável sozinho ainda não garante a página inicial.
                abrir.assert_not_called()
            finally:
                self.deixar_pronto()
                tarefa.join(timeout=5)
            self.assertFalse(tarefa.is_alive(), 'A espera de inicialização não terminou.')
            self.assertEqual(erros, [])
            self.assertEqual(resultado, [True])
            abrir.assert_called_once()
            self.assertEqual(abrir.call_args.args[0], self.url + '/index.html')

    def test_saude_503_expira_sem_abrir_navegador(self):
        self.estado.index_pronto.set()
        self.assert_indisponivel()
        self.assertTrue(self.estado.recebeu_saude.is_set())

    def test_http_200_com_saude_invalida_nao_e_prontidao(self):
        self.deixar_pronto()
        self.estado.status_saude = 'erro'
        self.assert_indisponivel()

    def test_index_503_expira_mesmo_com_banco_saudavel(self):
        self.estado.saude_pronta.set()
        self.assert_indisponivel()
        self.assertTrue(self.estado.recebeu_index.is_set())

    def test_outra_pagina_na_porta_nao_abre_como_evofit(self):
        self.deixar_pronto()
        self.estado.titulo = 'Outro aplicativo'
        # O texto EvoFit no corpo não transforma outra página no index esperado.
        self.assert_indisponivel()

    def test_navegador_ausente_retorna_false_e_servico_continua_disponivel(self):
        self.deixar_pronto()
        with mock.patch('tools.abrir_index.webbrowser.open', return_value=False) as abrir:
            self.assertFalse(abrir_index_pronto(
                self.url, timeout=1, intervalo=0.02
            ))
            abrir.assert_called_once()
            self.assertEqual(abrir.call_args.args[0], self.url + '/index.html')
        # A indisponibilidade do navegador não deve desligar o servidor pronto.
        with urlopen(self.url + '/api/saude', timeout=1) as resposta:
            self.assertEqual(resposta.status, 200)
        with urlopen(self.url + '/index.html', timeout=1) as resposta:
            self.assertEqual(resposta.status, 200)

    def test_erro_do_controlador_de_navegador_nao_vira_falha_do_servidor(self):
        self.deixar_pronto()
        with mock.patch('tools.abrir_index.webbrowser.open', side_effect=webbrowser.Error('Sem navegador')):
            self.assertFalse(abrir_index_pronto(
                self.url, timeout=1, intervalo=0.02
            ))
        with urlopen(self.url + '/api/saude', timeout=1) as resposta:
            self.assertEqual(json.load(resposta)['status'], 'ok')

    def test_conexao_recusada_expira_sem_abrir(self):
        self.servidor.shutdown()
        self.servidor.server_close()
        self.parado = True
        self.assert_indisponivel()


if __name__ == '__main__':
    unittest.main()
