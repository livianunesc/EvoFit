"""Abre a página inicial somente depois de confirmar a prontidão do EvoFit.

O inicializador local e o inicializador Docker reutilizam a mesma verificação.
Este módulo usa apenas a biblioteca padrão e não inicia serviços por conta própria.
"""
from html.parser import HTMLParser
from http.client import HTTPException
import json
import sys
import time
from urllib.error import URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener
import webbrowser


class _TituloHTML(HTMLParser):
    """Lê o título da página, sem confundir texto de scripts com a tag title."""

    def __init__(self):
        super().__init__()
        self.no_titulo = False
        self.partes = []

    def handle_starttag(self, tag, attrs):
        if tag == 'title':
            self.no_titulo = True

    def handle_endtag(self, tag):
        if tag == 'title':
            self.no_titulo = False

    def handle_data(self, texto):
        if self.no_titulo:
            self.partes.append(texto)


class _SemRedirecionamento(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # A prontidão deve vir do endereço solicitado, não de uma página de login externa.
        return None


def abrir_index_pronto(url_base, timeout=30.0, intervalo=0.2, timeout_requisicao=2.0):
    """Retorna True se o navegador aceitar a abertura após API e HTML prontos.

    Retorna False com um aviso local quando o tempo termina ou não há navegador.
    ``timeout`` limita a espera total; cada requisição também possui limite próprio.
    O chamador local deve reservar a porta antes de chamar esta função, para não
    confundir um serviço já existente com o servidor que está sendo iniciado.
    """
    endereco = urlsplit(url_base)
    if (endereco.scheme not in ('http', 'https') or not endereco.hostname
            or endereco.username is not None or endereco.password is not None
            or endereco.query or endereco.fragment):
        raise ValueError('Informe a URL base HTTP do servidor, sem credenciais ou parâmetros.')
    if timeout < 0 or intervalo <= 0 or timeout_requisicao <= 0:
        raise ValueError('Timeout não pode ser negativo; intervalo e tempo de requisição devem ser positivos.')
    base = urlunsplit((endereco.scheme, endereco.netloc, endereco.path.rstrip('/'), '', ''))
    url_index = base + '/index.html'
    url_saude = base + '/api/saude'
    # A navegação é local: não enviamos essas consultas a proxies do ambiente.
    cliente = build_opener(ProxyHandler({}), _SemRedirecionamento())
    limite = time.monotonic() + timeout

    def ler(url, tamanho):
        restante = limite - time.monotonic()
        if restante <= 0:
            raise TimeoutError
        with cliente.open(url, timeout=min(timeout_requisicao, restante)) as resposta:
            if resposta.status != 200:
                raise ValueError('O serviço ainda não está pronto.')
            conteudo = resposta.read(tamanho + 1)
            if len(conteudo) > tamanho:
                raise ValueError('Resposta de prontidão inesperada.')
            return conteudo.decode('utf-8')

    while time.monotonic() < limite:
        try:
            saude = json.loads(ler(url_saude, 8192))
            if not isinstance(saude, dict) or saude.get('status') != 'ok':
                raise ValueError('A conexão do EvoFit ainda não está pronta.')
            pagina = _TituloHTML()
            pagina.feed(ler(url_index, 65_536))
            if 'evofit' not in ''.join(pagina.partes).casefold():
                raise ValueError('A página inicial do EvoFit ainda não está disponível.')
        except (URLError, OSError, TimeoutError, ValueError, UnicodeError, HTTPException):
            restante = limite - time.monotonic()
            if restante > 0:
                time.sleep(min(intervalo, restante))
            continue
        try:
            if webbrowser.open(url_index, new=2):
                return True
        except (webbrowser.Error, OSError):
            pass
        print(f'O EvoFit está pronto, mas o navegador padrão não pôde ser aberto. Abra {url_index}',
              file=sys.stderr)
        return False

    print(f'O EvoFit ainda não ficou pronto no tempo esperado. Confira o servidor e o banco antes de abrir {url_index}',
          file=sys.stderr)
    return False
