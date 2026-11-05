"""Real-browser PHP/MySQL workflow; requires an explicitly selected test instance.

    EVOFIT_TEST_URL=http://127.0.0.1:4174 python3 tests/browser_php.py

Creates unique linked test accounts, never edits demo records or deletes user data.
"""
import os
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from test_php_flow import ApiClient
from playwright.sync_api import sync_playwright, expect


def run():
    base = os.environ.get('EVOFIT_TEST_URL', '').rstrip('/') + '/'
    if not os.environ.get('EVOFIT_TEST_URL'):
        raise SystemExit('Defina EVOFIT_TEST_URL para uma instância PHP/MySQL dedicada a testes.')
    suffix = uuid.uuid4().hex
    trainer_email, student_email = f'browser-trainer-{suffix}@example.com', f'browser-student-{suffix}@example.com'
    trainer_api, student_api = ApiClient(base), ApiClient(base)
    trainer_api.request('register', {'name': 'Personal navegador', 'email': trainer_email,
                                     'role': 'personal', 'password': 'Teste123!'})
    trainer_api.request('student', {'name': 'Aluno navegador', 'email': student_email, 'password': 'Teste123!',
                                    'goal': 'Evoluir com consistência'})
    student_id = next(s['id'] for s in trainer_api.request('state')['students'] if s['email'] == student_email)
    xss_notes = '<img src=x onerror="window.evofitInjected=true"> Controle a descida.'
    workouts = [
        ('Posterior / Glúteo', [dict(name='Agachamento', sets=3, reps='12', load=20, rest=60, notes='Controle a descida.')]),
        ('Superior I', [dict(name='Remada', sets=3, reps='10', load=15, rest=60, notes='Aproxime as escápulas.')]),
        ('Quadríceps', [dict(name='Cadeira extensora', sets=4, reps='12', load=20, rest=60, notes=xss_notes,
                            illustration='extension'),
                       dict(name='Agachamento', sets=3, reps='12', load=15, rest=90, notes='Coluna neutra.')])
    ]
    for title, items in workouts:
        trainer_api.request('plan', {'student': student_id, 'kind': 'workout', 'title': title, 'items': items})
    trainer_api.request('plan', {'student': student_id, 'kind': 'diet', 'title': 'Plano do aluno',
                                'items': [dict(name='Almoço', time='12:30', food='Arroz e feijão', quantity='180 g')]})
    student_api.login(student_email, 'aluno', 'Teste123!')
    with tempfile.TemporaryDirectory() as temp, sync_playwright() as p:
        artifacts = Path(os.environ.get('EVOFIT_ARTIFACTS', temp))
        artifacts.mkdir(parents=True, exist_ok=True)
        browser = p.chromium.launch(headless=True, executable_path=os.environ.get('CHROMIUM_PATH') or
                                    shutil.which('chromium') or shutil.which('google-chrome'), args=['--no-sandbox'])
        student_context = browser.new_context(viewport=dict(width=1440, height=1000))
        trainer_context = browser.new_context(viewport=dict(width=1440, height=1000))
        page, personal = student_context.new_page(), trainer_context.new_page()
        errors, bad_responses = [], []

        def record_response(response):
            route = parse_qs(urlparse(response.url).query).get('route', [''])[0]
            initial_state = response.status == 401 and (route == 'state' or response.url.endswith('/api/state'))
            if response.status >= 400 and not initial_state and not response.url.endswith('/favicon.ico'):
                bad_responses.append((response.status, response.url))

        for tab in (page, personal):
            tab.on('pageerror', lambda error: errors.append(str(error)))
            tab.on('response', record_response)

        def login(tab, email, role):
            tab.goto(base)
            tab.get_by_label('E-mail', exact=True).fill(email)
            tab.get_by_label('Senha', exact=True).fill('Teste123!')
            tab.get_by_label('Seu perfil').select_option(role)
            tab.get_by_role('button', name='Entrar na minha conta').click()
            tab.locator('nav').wait_for()

        def nav(tab, name):
            tab.locator('nav').get_by_role('button', name=name).click()

        try:
            login(page, student_email, 'aluno')
            nav(page, 'Alimentação')
            expect(page.locator('#content')).to_contain_text('Arroz e feijão')
            nav(page, 'Treinos')
            expect(page.locator('.workout-card')).to_have_count(3)
            page.screenshot(path=str(artifacts / 'EvoFit-PHP-cards.png'), full_page=True)
            page.get_by_role('button', name='Iniciar treino: Quadríceps', exact=True).click()
            expect(page.get_by_role('button', name='Concluir treino', exact=False)).to_be_disabled()
            details = page.locator('details').first
            details.locator('summary').click()
            expect(details.get_by_role('heading', name='Cadeira extensora')).to_be_visible()
            expect(details.locator('.exercise-metrics')).to_contain_text('60')
            expect(details.locator('.exercise-instructions')).to_have_text(xss_notes)
            assert not page.evaluate('Boolean(window.evofitInjected)'), 'Stored HTML was executed'
            assert details.locator('img').evaluate('(img)=>img.complete && img.naturalWidth>0'), 'Exercise image did not load'
            details.get_by_role('button', name='Aumentar carga de Cadeira extensora', exact=True).click()
            expect(details.get_by_role('spinbutton')).to_have_value('20.5')
            details.get_by_role('spinbutton').fill('25')
            page.screenshot(path=str(artifacts / 'EvoFit-PHP-exercicio.png'), full_page=True)
            # Hold the request to verify input locking and keyboard focus during asynchronous persistence.
            page.evaluate('''() => {
              const originalFetch=window.fetch;
              window.holdExercise=true;
              window.fetch=(url,options) => {
                const request=new URL(url,location.href);
                const isExercise=request.searchParams.get('route')==='exercise' || request.pathname.endsWith('/api/exercise');
                return isExercise && window.holdExercise
                  ? new Promise(resolve => {window.releaseExercise=()=>{window.holdExercise=false;resolve(originalFetch(url,options));};})
                  : originalFetch(url,options);
              };
            }''')
            details.get_by_role('button', name='Concluir exercício', exact=False).click()
            expect(details.get_by_role('spinbutton')).to_be_disabled()
            expect(details.get_by_role('button', name='Aumentar carga de Cadeira extensora', exact=True)).to_be_disabled()
            page.evaluate('window.releaseExercise()')
            expect(page.locator('.workout-progress strong')).to_contain_text('1')
            assert page.evaluate('document.activeElement.tagName') == 'SUMMARY', 'Focus lost after saving'
            page.reload()
            page.locator('nav').wait_for()
            nav(page, 'Treinos')
            page.get_by_role('button', name='Retomar treino: Quadríceps', exact=True).click()
            details = page.locator('details').first
            details.locator('summary').click()
            expect(details.get_by_role('spinbutton')).to_have_value('25')
            expect(details.get_by_role('button', name='Exercício concluído', exact=False)).to_be_disabled()
            details.get_by_role('button', name='Ajustar carga').click()
            expect(details.get_by_role('spinbutton')).to_be_enabled()
            details.get_by_role('spinbutton').fill('27.5')
            details.get_by_role('button', name='Concluir exercício', exact=False).click()
            expect(page.locator('.workout-progress strong')).to_contain_text('1')
            login(personal, trainer_email, 'personal')
            nav(personal, 'Treinos')
            personal.get_by_role('button', name='Ver treino: Quadríceps', exact=True).click()
            expect(personal.locator('.workout-progress strong')).to_contain_text('1')
            expect(personal.locator('[data-complete-exercise]')).to_have_count(0)
            other = page.locator('details').nth(1)
            other.locator('summary').click()
            other.get_by_role('button', name='Concluir exercício', exact=False).click()
            expect(page.get_by_role('button', name='Concluir treino', exact=False)).to_be_enabled()
            page.get_by_label('Observações do treino', exact=True).fill('Treino completo com PHP e MySQL')
            page.get_by_role('button', name='Concluir treino', exact=False).click()
            expect(page.get_by_role('heading', name='Treinos registrados')).to_be_visible()
            expect(page.locator('#content')).to_contain_text('Cadeira extensora · 27.5 kg')
            expect(page.locator('#content')).to_contain_text('Treino completo com PHP e MySQL')
            personal.reload()
            personal.locator('nav').wait_for()
            nav(personal, 'Histórico')
            expect(personal.locator('#content')).to_contain_text('Cadeira extensora · 27.5 kg')
            # Personal creates/edits plans through existing forms with PHP persistence.
            nav(personal, 'Treinos')
            personal.locator('.workout-tile').filter(has_text='Quadríceps').get_by_role('button', name='Editar treino').click()
            personal.locator('.editor').first.get_by_label('Imagem do exercício').select_option('extension')
            personal.locator('.editor').first.get_by_label('Instruções / observações').fill('Mantenha as costas apoiadas e controle a descida.')
            personal.get_by_label('Título / dia / divisão').fill('Quadríceps atualizado')
            personal.get_by_role('button', name='Salvar e atribuir').click()
            expect(personal.locator('.workout-grid')).to_be_visible()
            page.reload()
            page.locator('nav').wait_for()
            nav(page, 'Treinos')
            expect(page.get_by_role('button', name='Iniciar treino: Quadríceps atualizado', exact=True)).to_be_visible()
            page.get_by_role('button', name='Iniciar treino: Quadríceps atualizado', exact=True).click()
            page.locator('details').first.locator('summary').click()
            page.evaluate("document.querySelector('#toast').style.display='none'")
            page.screenshot(path=str(artifacts / 'EvoFit-PHP-exercicio.png'), full_page=True)
            page.get_by_role('button', name='Todos os treinos', exact=False).click()
            page.set_viewport_size(dict(width=390, height=844))
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile cards overflow'
            page.get_by_role('button', name='Iniciar treino: Quadríceps atualizado', exact=True).click()
            if not page.locator('details').first.evaluate('(el)=>el.open'):
                page.locator('details').first.locator('summary').click()
            page.evaluate("document.querySelector('#toast').style.display='none'")
            page.screenshot(path=str(artifacts / 'EvoFit-PHP-mobile.png'), full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile exercise overflow'
            page.locator('details').first.locator('summary').focus()
            page.keyboard.press('Enter')
            assert not page.locator('details').first.evaluate('(el)=>el.open'), 'Keyboard toggle did not close the exercise'
            assert len(student_api.request('state')['logs']) == 1, 'Completed workout was not persisted once'
            assert not errors, errors
            assert not bad_responses, bad_responses
            print('PASS: PHP/MySQL browser login, diet, cards, accordion, images, escaped stored HTML, loads, asynchronous lock, focus, reload/resume, personal synchronization, history, edit form and mobile keyboard flow.')
        finally:
            student_context.close()
            trainer_context.close()
            browser.close()


if __name__ == '__main__':
    run()
