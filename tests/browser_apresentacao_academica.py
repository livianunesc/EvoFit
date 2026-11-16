"""Fluxo real da apresentação: somente contra instância/banco exclusivo de testes.

Requer servidor inicializado com seed e Playwright/Chromium instalados.
O fluxo acrescenta uma conclusão de treino à conta demo; não apaga dados.
Veja apresentacao/README.md para execução e confirmação do banco de testes.
"""
import os
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright, expect

expect.set_options(timeout=30000)
# Sem endereço padrão: a execução precisa apontar conscientemente para a instância de testes.
BASE = os.environ.get('EVOFIT_TEST_URL', '').rstrip('/')
if not BASE:
    raise SystemExit('Defina EVOFIT_TEST_URL para uma instância EXCLUSIVA de testes (ex.: http://127.0.0.1:4185).')
if os.environ.get('EVOFIT_CONFIRMAR_BANCO_TESTE') != '1':
    raise SystemExit('Confirme que a URL usa banco exclusivo de testes: EVOFIT_CONFIRMAR_BANCO_TESTE=1. O teste grava um treino demo.')
if urlparse(BASE).scheme not in ('http', 'https') or not urlparse(BASE).hostname:
    raise SystemExit('EVOFIT_TEST_URL deve ser uma URL HTTP/HTTPS válida.')

# Funciona em Windows/Linux: use o browser instalado pelo Playwright ou um caminho explícito.
chromium = os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
capturas = Path(os.environ['EVOFIT_SCREENSHOT_DIR']) if os.environ.get('EVOFIT_SCREENSHOT_DIR') else Path(tempfile.mkdtemp(prefix='evofit-apresentacao-'))
capturas.mkdir(parents=True, exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True, executable_path=chromium, args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1280,'height':1000}, reduced_motion='reduce')
    page=context.new_page()
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type=='error' and '401 (UNAUTHORIZED)' not in msg.text else None)
    page.on('response', lambda response: errors.append(f'HTTP {response.status}: {response.url}') if response.status>=400 and not (response.status==401 and response.url.endswith('/api/sessao')) else None)
    def get(route):
        response=context.request.get(BASE+'/api/'+route)
        assert response.ok, (route,response.status,response.text())
        return response.json()
    page.goto(BASE+'/apresentacao/')
    expect(page.get_by_role('heading', name='Entrar no EvoFit')).to_be_visible()
    page.get_by_role('button', name='Preencher conta de exemplo').click()
    page.get_by_role('button', name='Entrar', exact=True).click()
    expect(page.locator('#painel')).to_be_visible()
    expect(page.locator('#form-treino')).to_be_visible()
    aluno=get('sessao')['usuario']
    anterior=len(get('historico')['registros'])
    ranking_antes={item['aluno_id']: item['total'] for item in get('ranking')['ranking']}
    expect(page.get_by_role('button', name='Concluir treino', exact=True)).to_be_disabled()
    assert page.locator('[data-feito]').count()>0
    for box in page.locator('[data-feito]').all(): box.check()
    for carga in page.locator('[data-carga]').all(): carga.fill('12.50')
    page.get_by_role('button', name='Concluir treino', exact=True).click()
    expect(page.locator('#mensagem')).to_contain_text('Treino registrado!')
    expect(page.locator('#concluir')).to_be_disabled()
    historico=get('historico')['registros']
    assert len(historico)==anterior+1
    ranking_depois={item['aluno_id']: item['total'] for item in get('ranking')['ranking']}
    assert ranking_depois[aluno['id']]==ranking_antes[aluno['id']]+1
    assert page.locator('#historico li').count()>0
    page.screenshot(path=str(capturas / 'apresentacao-desktop.png'), full_page=True)
    page.set_viewport_size({'width':375,'height':812})
    assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth'), 'Overflow mobile'
    page.screenshot(path=str(capturas / 'apresentacao-mobile.png'), full_page=True)
    page.reload()
    expect(page.locator('#painel')).to_be_visible()
    assert len(get('historico')['registros'])==anterior+1, 'Persistência no reload'
    page.get_by_role('button', name='Sair', exact=True).click()
    expect(page.locator('#acesso')).to_be_visible()
    page.locator('#email').fill('personal@evofit.demo')
    page.locator('#senha').fill('EvoFit123!')
    page.get_by_role('button', name='Entrar', exact=True).click()
    expect(page.locator('#painel')).to_be_visible()
    expect(page.locator('#form-treino')).to_be_visible()
    expect(page.locator('#concluir')).to_be_hidden()
    assert page.locator('[data-feito]').count()==0
    for carga in page.locator('[data-carga]').all(): expect(carga).to_be_disabled()
    expect(page.locator('#orientacao')).to_contain_text('personal consulta')
    page.get_by_role('button', name='Sair', exact=True).click()
    expect(page.locator('#acesso')).to_be_visible()
    assert not errors, errors
    browser.close()
print('PASS: apresentação; login aluno/personal, checkbox/carga, conclusão MySQL, histórico +1, ranking +1, reload persistente, personal readonly, 375px sem overflow, logout e sem erros JavaScript.')

print(f'Capturas: {capturas.resolve()}')
