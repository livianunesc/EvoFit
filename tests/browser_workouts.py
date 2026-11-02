"""Functional UI test. Requires Playwright and a Chromium browser (not runtime dependencies)."""
import tempfile, threading, sys, json, os, shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import server
from playwright.sync_api import sync_playwright, expect

def run():
    with tempfile.TemporaryDirectory() as temp:
        server.DB=str(Path(temp)/'browser.sqlite3');server.init()
        artifacts=Path(os.environ.get('EVOFIT_ARTIFACTS',temp));artifacts.mkdir(parents=True,exist_ok=True)
        with server.connect() as d:
            d.execute('INSERT INTO plans(student,kind,title,items) VALUES(2,?,?,?)',('workout','Quadríceps',json.dumps([
                dict(name='Cadeira extensora',sets=4,reps='12',load=20,rest=60,notes='Mantenha as costas apoiadas e controle a descida.'),
                dict(name='Agachamento',sets=3,reps='12',load=15,rest=90,notes='Mantenha a coluna neutra.')
            ])))
        http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=http.serve_forever,daemon=True).start()
        try:
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True,executable_path=os.environ.get('CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
                page=browser.new_page(viewport=dict(width=1440,height=1000))
                errors=[];bad_responses=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                page.on('response',lambda response:bad_responses.append((response.status,response.url)) if response.status>=400 and not response.url.endswith('/api/state') else None)
                base='http://127.0.0.1:'+str(http.server_port)
                def login(email,role):
                    page.goto(base)
                    page.get_by_label('E-mail',exact=True).fill(email)
                    page.get_by_label('Senha',exact=True).fill('EvoFit123!')
                    page.get_by_label('Seu perfil').select_option(role)
                    page.get_by_role('button',name='Entrar na minha conta').click()
                    page.locator('nav').wait_for()
                def nav(tab):page.locator('nav').get_by_role('button',name=tab).click()
                login('aluno@evofit.demo','aluno');nav('Treinos')
                expect(page.locator('.workout-card')).to_have_count(3)
                page.screenshot(path=str(artifacts/'EvoFit-treinos-cards.png'),full_page=True)
                page.get_by_role('button',name='Iniciar treino: Quadríceps',exact=True).click()
                expect(page.get_by_role('button',name='Concluir treino',exact=False)).to_be_disabled()
                details=page.locator('details').filter(has=page.locator('summary strong',has_text='Cadeira extensora'))
                details.locator('summary').click()
                expect(details.get_by_role('heading',name='Cadeira extensora')).to_be_visible()
                expect(details.locator('.exercise-metrics')).to_contain_text('60')
                assert details.locator('img').evaluate('(img)=>img.complete && img.naturalWidth > 0')
                details.get_by_role('button',name='Aumentar carga de Cadeira extensora',exact=True).click()
                load=details.get_by_role('spinbutton');expect(load).to_have_value('20.5')
                load.fill('25')
                page.screenshot(path=str(artifacts/'EvoFit-exercicio.png'),full_page=True)
                page.evaluate('''() => {
                  const originalFetch=window.fetch;
                  window.holdExercise=true;
                  window.fetch=(url,options) => String(url).endsWith('/api/exercise') && window.holdExercise
                    ? new Promise(resolve => {window.releaseExercise=()=>{window.holdExercise=false;resolve(originalFetch(url,options));};})
                    : originalFetch(url,options);
                }''')
                details.get_by_role('button',name='Concluir exercício',exact=False).click()
                expect(details.get_by_role('spinbutton')).to_be_disabled()
                expect(details.get_by_role('button',name='Aumentar carga de Cadeira extensora',exact=True)).to_be_disabled()
                page.evaluate('window.releaseExercise()')
                expect(page.locator('.workout-progress strong')).to_contain_text('1')
                assert page.evaluate('document.activeElement.tagName')=='SUMMARY','Focus lost after saving'
                # Refresh and login sessions must not lose per-exercise completion or load.
                page.reload();page.locator('nav').wait_for();nav('Treinos')
                page.get_by_role('button',name='Retomar treino: Quadríceps',exact=True).click()
                details=page.locator('details').first;details.locator('summary').click()
                expect(details.get_by_role('spinbutton')).to_have_value('25')
                expect(details.get_by_role('button',name='Exercício concluído',exact=False)).to_be_disabled()
                details.get_by_role('button',name='Ajustar carga').click()
                expect(details.get_by_role('spinbutton')).to_be_enabled()
                details.get_by_role('spinbutton').fill('27.5')
                details.get_by_role('button',name='Concluir exercício',exact=False).click()
                expect(page.locator('.workout-progress strong')).to_contain_text('1')
                # Personal can see saved progress, without student-only controls.
                ctx=browser.new_context();trainer=ctx.new_page();trainer.goto(base)
                trainer.get_by_label('E-mail',exact=True).fill('personal@evofit.demo');trainer.get_by_label('Senha',exact=True).fill('EvoFit123!');trainer.get_by_label('Seu perfil').select_option('personal');trainer.get_by_role('button',name='Entrar na minha conta').click();trainer.locator('nav').wait_for()
                trainer.locator('nav').get_by_role('button',name='Treinos').click();trainer.get_by_role('button',name='Ver treino: Quadríceps',exact=True).click()
                expect(trainer.locator('.workout-progress strong')).to_contain_text('1')
                expect(trainer.locator('[data-complete-exercise]')).to_have_count(0)
                # Finish second exercise, then entire workout: one real history record.
                other=page.locator('details').nth(1);other.locator('summary').click();other.get_by_role('button',name='Concluir exercício',exact=False).click()
                expect(page.get_by_role('button',name='Concluir treino',exact=False)).to_be_enabled()
                page.get_by_label('Observações do treino',exact=True).fill('Treino completo no navegador')
                page.get_by_role('button',name='Concluir treino',exact=False).click()
                expect(page.get_by_role('heading',name='Treinos registrados')).to_be_visible()
                expect(page.locator('#content')).to_contain_text('Cadeira extensora · 27.5 kg')
                expect(page.locator('#content')).to_contain_text('Treino completo no navegador')
                trainer.reload();trainer.locator('nav').wait_for();trainer.locator('nav').get_by_role('button',name='Histórico').click();expect(trainer.locator('#content')).to_contain_text('Cadeira extensora · 27.5 kg')
                # Personal edit UI persists the illustration choice; saves remain compatible.
                trainer.locator('nav').get_by_role('button',name='Treinos').click();trainer.locator('.workout-tile').filter(has_text='Quadríceps').get_by_role('button',name='Editar treino').click()
                trainer.locator('.editor').first.get_by_label('Imagem do exercício').select_option('extension')
                trainer.get_by_role('button',name='Salvar e atribuir').click();expect(trainer.locator('.workout-grid')).to_be_visible()
                nav('Treinos');page.set_viewport_size(dict(width=390,height=844))
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile cards overflow'
                page.get_by_role('button',name='Iniciar treino: Quadríceps',exact=True).click();page.locator('details').first.locator('summary').click()
                page.evaluate("document.querySelector('#toast').style.display='none'")
                page.screenshot(path=str(artifacts/'EvoFit-exercicio-celular.png'),full_page=True)
                assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),'Mobile exercise overflow'
                # Keyboard-native details toggles and loaded local illustrations.
                page.locator('details').first.locator('summary').focus();page.keyboard.press('Enter');assert not page.locator('details').first.evaluate('(el)=>el.open')
                assert not errors,errors
                assert not bad_responses,bad_responses
                print('PASS: cards, accordion, images, load controls, exercise completion, reload/resume, edit load, whole-workout history, personal synchronization, illustration editing, mobile layout, keyboard and no JS errors.')
                ctx.close();browser.close()
        finally:http.shutdown();http.server_close()
if __name__=='__main__':run()
