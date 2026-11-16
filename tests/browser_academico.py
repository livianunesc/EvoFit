"""Fluxo de navegador da versão acadêmica. Requer Playwright e Chromium.

Use EVOFIT_TEST_URL e EVOFIT_CONFIRMAR_BANCO_TESTE=1 em banco exclusivo de testes. O teste cria fixtures únicas;
apenas as fixtures explicitamente descartáveis são excluídas. Contas demo não
são alteradas. EVOFIT_SCREENSHOT_DIR é opcional; por padrão usa pasta temporária.
"""
from pathlib import Path
import os
import tempfile
import shutil
from uuid import uuid4
from playwright.sync_api import sync_playwright, expect

BASE=os.environ.get('EVOFIT_TEST_URL', '').rstrip('/')
if not BASE or os.environ.get('EVOFIT_CONFIRMAR_BANCO_TESTE') != '1':
 raise SystemExit('Defina EVOFIT_TEST_URL e EVOFIT_CONFIRMAR_BANCO_TESTE=1 para uma instância exclusiva de testes; nunca use o banco principal.')
slug=uuid4().hex[:8]
nome=f'Aluno Browser {slug}'
email=f'browser-{slug}@example.com'
senha='Teste123!'
mov=f'Movimento Browser {slug}'
titulo=f'Treino Browser {slug}'
art=Path(os.environ.get('EVOFIT_SCREENSHOT_DIR') or tempfile.mkdtemp(prefix='evofit-browser-'));art.mkdir(parents=True,exist_ok=True)
errors=[]
def login(page, email, senha):
 page.goto(BASE+'/')
 page.get_by_label('E-mail', exact=True).fill(email)
 page.get_by_label('Senha', exact=True).fill(senha)
 page.get_by_role('button',name='Entrar no EvoFit').click()
 expect(page.locator('#painel')).to_be_visible()
 expect(page.locator('#total-treinos')).not_to_have_text('—')
 expect(page.locator('#status')).to_be_empty()
 page.evaluate('document.fonts.ready')
def sucesso(page,text): expect(page.locator('#status')).to_contain_text(text)
def verificar_exclusoes(page):
 # Fixtures exclusivas de teste: nenhuma conta demonstrativa é removida.
 page.set_viewport_size({'width':1366,'height':900})
 page.get_by_role('button',name='Sair',exact=True).click()
 expect(page.locator('#entrada')).to_be_visible()
 login(page,'personal@evofit.demo','EvoFit123!')
 page.get_by_role('link',name='Alunos',exact=True).click()
 expect(page.locator('#area-restrita')).to_be_visible()
 nome_temp='Temporário '+slug
 email_temp='excluir-'+slug+'@example.com'
 page.get_by_label('Nome completo').fill(nome_temp)
 page.get_by_label('E-mail',exact=True).fill(email_temp)
 page.get_by_label('Senha inicial').fill(senha)
 page.get_by_label('Objetivo',exact=True).fill('Fixture descartável')
 page.get_by_role('button',name='Cadastrar aluno',exact=True).click();sucesso(page,'Aluno cadastrado')
 page.get_by_role('link',name='Exercícios',exact=True).click()
 expect(page.locator('#area-restrita')).to_be_visible()
 mov_temp='Temporário '+slug
 page.get_by_label('Nome',exact=True).fill(mov_temp)
 page.get_by_label('Grupo muscular').fill('Pernas')
 page.get_by_label('Instruções',exact=True).fill('Fixture descartável.')
 page.get_by_role('button',name='Cadastrar exercício',exact=True).click();sucesso(page,'Exercício cadastrado')
 page.get_by_role('link',name='Treinos',exact=True).click()
 expect(page.locator('#editor-treino')).to_be_visible()
 page.get_by_label('Aluno',exact=True).select_option(label=nome_temp)
 titulo_temp='Temporário '+slug
 page.get_by_label('Título do treino').fill(titulo_temp)
 page.get_by_label('Exercício',exact=True).select_option(label=mov_temp+' · Pernas')
 page.get_by_role('button',name='Salvar treino',exact=True).click();sucesso(page,'Treino prescrito')
 page.once('dialog',lambda dialog:dialog.accept())
 page.locator('article.treino').filter(has_text=titulo_temp).get_by_role('button',name='Excluir treino').click();sucesso(page,'Treino excluído')
 expect(page.locator('article.treino').filter(has_text=titulo_temp)).to_have_count(0)
 page.get_by_role('link',name='Exercícios',exact=True).click()
 expect(page.locator('#lista-exercicios')).to_contain_text(mov_temp)
 page.once('dialog',lambda dialog:dialog.accept())
 page.get_by_role('row').filter(has_text=mov_temp).get_by_role('button',name='Excluir',exact=True).click();sucesso(page,'Exercício excluído')
 expect(page.get_by_role('row').filter(has_text=mov_temp)).to_have_count(0)
 page.get_by_role('link',name='Alunos',exact=True).click()
 expect(page.locator('#lista-alunos')).to_contain_text(email_temp)
 page.once('dialog',lambda dialog:dialog.accept())
 page.get_by_role('row').filter(has_text=email_temp).get_by_role('button',name='Excluir',exact=True).click();sucesso(page,'Aluno excluído')
 expect(page.get_by_role('row').filter(has_text=email_temp)).to_have_count(0)

with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1366,'height':900})
 page=context.new_page();page.set_default_timeout(60000);page.on('pageerror',lambda e:errors.append(str(e)))
 login(page,'personal@evofit.demo','EvoFit123!')
 page.screenshot(path=str(art/'painel-personal.png'),full_page=True)
 page.get_by_role('link',name='Alunos',exact=True).click()
 expect(page.locator('#area-restrita')).to_be_visible()
 page.get_by_label('Nome completo').fill(nome)
 page.get_by_label('E-mail',exact=True).fill(email)
 page.get_by_label('Senha inicial').fill(senha)
 page.get_by_label('Objetivo',exact=True).fill('Força e foco')
 page.get_by_role('button',name='Cadastrar aluno',exact=True).click();sucesso(page,'Aluno cadastrado')
 row=page.get_by_role('row').filter(has_text=email)
 row.get_by_role('button',name='Editar',exact=True).click()
 page.get_by_label('Objetivo',exact=True).fill('Consistência semanal')
 page.get_by_role('button',name='Salvar alterações',exact=True).click();sucesso(page,'Cadastro atualizado')
 expect(row).to_contain_text('Consistência semanal')
 page.get_by_role('link',name='Exercícios',exact=True).click()
 expect(page.locator('#area-restrita')).to_be_visible()
 page.get_by_label('Nome',exact=True).fill(mov)
 page.get_by_label('Grupo muscular').fill('Pernas')
 page.get_by_label('Instruções',exact=True).fill('Execute com controle e sem pressa.')
 page.get_by_role('button',name='Cadastrar exercício',exact=True).click();sucesso(page,'Exercício cadastrado')
 row=page.get_by_role('row').filter(has_text=mov)
 row.get_by_role('button',name='Editar',exact=True).click()
 page.get_by_label('Instruções',exact=True).fill('Desça de forma controlada.')
 page.get_by_role('button',name='Salvar alterações',exact=True).click();sucesso(page,'Exercício atualizado')
 page.get_by_role('link',name='Treinos',exact=True).click()
 expect(page.locator('#editor-treino')).to_be_visible()
 page.get_by_label('Aluno',exact=True).select_option(label=nome)
 page.get_by_label('Título do treino').fill(titulo)
 page.get_by_label('Exercício',exact=True).select_option(label=mov+' · Pernas')
 page.get_by_label('Carga (kg)',exact=True).fill('25')
 page.get_by_role('button',name='Salvar treino',exact=True).click();sucesso(page,'Treino prescrito')
 treino=page.locator('article.treino').filter(has_text=titulo)
 expect(treino).to_contain_text(mov)
 treino.get_by_role('button',name='Editar treino').click()
 page.get_by_label('Título do treino').fill(titulo+' revisado')
 page.get_by_role('button',name='Salvar treino',exact=True).click();sucesso(page,'Treino atualizado')
 expect(page.locator('article.treino').filter(has_text=titulo)).to_contain_text('revisado')
 page.get_by_role('button',name='Sair',exact=True).click()
 expect(page.locator('#entrada')).to_be_visible()
 login(page,email,senha)
 page.get_by_role('link',name='Treinos',exact=True).click()
 expect(page.locator('article.treino')).to_have_count(1)
 page.get_by_role('button',name='Concluir treino',exact=True).click();sucesso(page,'Marque cada exercício')
 page.get_by_label('Carga utilizada (kg)',exact=True).fill('27.5')
 page.get_by_label('Exercício concluído',exact=True).check()
 page.get_by_role('button',name='Concluir treino',exact=True).click();sucesso(page,'Treino concluído')
 page.get_by_role('link',name='Histórico e ranking',exact=True).click()
 expect(page.locator('#lista-historico')).to_contain_text(titulo+' revisado')
 expect(page.locator('#lista-historico')).to_contain_text('27,5 kg')
 expect(page.locator('#ranking-completo')).to_contain_text(nome)
 page.screenshot(path=str(art/'historico-aluno.png'),full_page=True)
 page.set_viewport_size({'width':375,'height':812})
 for path in ['/','/pages/treinos.html','/pages/relatorios.html']:
  page.goto(BASE+path);page.wait_for_load_state('networkidle')
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'Overflow horizontal em {path}'
 page.screenshot(path=str(art/'historico-mobile.png'),full_page=True)
 # Um aluno não vê as telas de manutenção do personal.
 page.goto(BASE+'/pages/alunos.html')
 expect(page.locator('#status')).to_contain_text('destinada ao personal')
 expect(page.locator('#area-restrita')).to_be_hidden()
 assert not errors,errors
 verificar_exclusoes(page)
 browser.close()
 print('PASS: login personal/aluno, CRUD completo aluno/exercício/treino, carga e conclusão validada, histórico/ranking e mobile375px sem overflow; sem erros JavaScript.')
