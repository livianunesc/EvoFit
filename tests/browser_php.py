"""Real-browser PHP/MySQL workflow; requires an explicitly selected test instance.

    EVOFIT_TEST_URL=http://127.0.0.1:4174 python3 tests/browser_php.py

Creates unique linked test accounts, never edits demo records or deletes user data.
"""
import os
import json
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from test_php_flow import ApiClient
from playwright.sync_api import sync_playwright, expect


def build_team_fixture(base):
    """Create real, isolated training records through the same public API as users."""
    suffix = uuid.uuid4().hex
    trainer_email = f'focus-trainer-{suffix}@example.com'
    trainer = ApiClient(base)
    trainer.request('register', {'name': 'Livia Foco', 'email': trainer_email,
                                 'role': 'personal', 'password': 'Teste123!'})
    students = []
    for slug, name in [('ana', 'Ana Silva'), ('bruno', 'Bruno Costa'), ('camila', 'Camila Nunes')]:
        email = f'focus-{slug}-{suffix}@example.com'
        trainer.request('student', {'name': name, 'email': email, 'password': 'Teste123!',
                                    'goal': 'Evoluir com consistência'})
        sid = next(person['id'] for person in trainer.request('state')['students'] if person['email'] == email)
        client = ApiClient(base)
        client.login(email, 'aluno', 'Teste123!')
        students.append(dict(id=sid, name=name, email=email, client=client))
    xss_notes = '<img src=x onerror="window.evofitInjected=true"> Controle a descida.'
    workouts = [
        ('Posterior / Glúteo', [dict(name='Agachamento', sets=3, reps='12', load=20, rest=60, notes='Controle a descida.')]),
        ('Superior I', [dict(name='Remada', sets=3, reps='10', load=15, rest=60, notes='Aproxime as escápulas.')]),
        ('Quadríceps', [dict(name='Cadeira extensora', sets=4, reps='12', load=20, rest=60, notes=xss_notes,
                            illustration='extension'),
                       dict(name='Agachamento', sets=3, reps='12', load=15, rest=90, notes='Coluna neutra.')]),
        ('Superior II', [dict(name='Supino', sets=3, reps='12', load=20, rest=90, notes='Controle a amplitude.')])
    ]
    for title, items in workouts:
        trainer.request('plan', {'student': students[0]['id'], 'kind': 'workout', 'title': title, 'items': items})
    # Training history and ranking are populated by genuine completed records, not UI constants.
    for person, completions in zip(students, [2, 3, 1]):
        if person is not students[0]:
            trainer.request('plan', {'student': person['id'], 'kind': 'workout', 'title': 'Treino funcional',
                                    'items': [dict(name='Agachamento', sets=3, reps='12', load=10, rest=60, notes='')]})
        plans = [plan for plan in person['client'].request('state')['plans'] if plan['kind'] == 'workout']
        for i in range(completions):
            plan = plans[i % len(plans)]
            person['client'].request('log', {'kind': 'workout', 'plan': plan['id'],
                'data': {'exercises': [dict(name=item['name'], load=item['load'], done=True) for item in plan['items']],
                         'notes': 'Registro de treino da equipe'}})
    outside = ApiClient(base)
    outside_email = f'focus-outsider-{suffix}@example.com'
    outside.request('register', {'name': 'Fora da equipe', 'email': outside_email,
                                 'role': 'aluno', 'password': 'Teste123!'})
    return dict(trainer=trainer, trainer_email=trainer_email, students=students, xss_notes=xss_notes,
                outside_email=outside_email,
                plans={plan['title']:plan['id'] for plan in students[0]['client'].request('state')['plans']})


def run():
    base = os.environ.get('EVOFIT_TEST_URL', '').rstrip('/') + '/'
    if not os.environ.get('EVOFIT_TEST_URL'):
        raise SystemExit('Defina EVOFIT_TEST_URL para uma instância PHP/MySQL dedicada a testes.')
    fixture = build_team_fixture(base)
    trainer_api = fixture['trainer']
    primary = fixture['students'][0]
    student_api = primary['client']
    trainer_email, student_email = fixture['trainer_email'], primary['email']
    student_id, xss_notes = primary['id'], fixture['xss_notes']
    initial_workouts = len([record for record in student_api.request('state')['logs'] if record['kind']=='workout'])
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

        def login(tab, email, role, *, navigate=True):
            if navigate:
                tab.goto(base)
            tab.get_by_label('E-mail', exact=True).fill(email)
            tab.get_by_label('Senha', exact=True).fill('Teste123!')
            tab.get_by_label('Tipo de acesso').select_option(role)
            tab.get_by_role('button', name='Entrar no EvoFit', exact=True).click()
            tab.locator('nav').wait_for()

        def nav(tab, name):
            tab.locator('nav').get_by_role('button', name=name, exact=True).click()

        def choose_workout(tab, title, *, open_details=True):
            plan_id = fixture['plans'][title]
            tab.locator(f'.workout-dots [data-feature-workout="{plan_id}"]').click()
            expect(tab.locator('.workout-active h2')).to_have_text(title)
            if open_details:
                tab.locator('.workout-start').click()

        def metric(tab, key, value):
            expect(tab.locator(f'[data-stat="{key}"] [data-count]')).to_have_text(value)

        def capture(tab, name, *, full_page=True):
            tab.evaluate('document.fonts.ready')
            tab.evaluate('window.scrollTo(0,0)')
            tab.screenshot(path=str(artifacts / name), full_page=full_page, animations='disabled')

        def assert_team_ranking(tab, period):
            with student_api.opener.open(student_api.base+'api.php?route=ranking&period='+period, timeout=20) as response:
                ranking=json.load(response)
            expected={person['id']:sum(record['kind']=='workout' for record in person['client'].request('state')['logs'])
                      for person in fixture['students']}
            assert {member['student']:member['completed'] for member in ranking['members']}==expected, 'Ranking did not match actual own-team logs'
            expect(tab.locator('.ranking-table [data-ranking-student]')).to_have_count(3)
            for person in fixture['students']:
                row=tab.locator(f'.ranking-table [data-ranking-student="{person["id"]}"]')
                expect(row).to_contain_text(person['name'])
                expect(row.locator('.ranking-total')).to_have_text(re.compile(rf'^{expected[person["id"]]}\s+concluídos$'))
            expect(tab.locator('#content')).not_to_contain_text('Fora da equipe')

        def assert_completed_history(tab):
            latest=tab.locator('.history-entry').first
            expect(latest.locator('summary')).to_contain_text('Quadríceps')
            exercise=latest.locator('.history-body > div').filter(has=tab.locator('span', has_text='Cadeira extensora'))
            expect(exercise.locator('strong')).to_have_text('27.5 kg')
            expect(latest.locator('.history-notes')).to_have_text('Treino completo com PHP e MySQL')

        def hold_ranking_refresh(tab):
            """Delay one genuine authenticated state response after its body arrives."""
            tab.evaluate('''() => {
                const originalFetch=window.fetch.bind(window);
                let holdOnce=true;
                window.evofitHeldStateReady=false;
                window.evofitHeldStateConsumed=false;
                window.fetch=async (url,options) => {
                    const request=new URL(url,location.href);
                    const isState=request.searchParams.get('route')==='state'
                        || request.pathname.endsWith('/api/state');
                    const shouldHold=holdOnce && isState;
                    if(shouldHold)holdOnce=false;
                    const response=await originalFetch(url,options);
                    if(!shouldHold)return response;
                    const captured=await response.clone().json();
                    window.evofitHeldStateUser=captured.user.id;
                    response.json=async () => {
                        setTimeout(()=>window.evofitHeldStateConsumed=true,0);
                        return captured;
                    };
                    return await new Promise(resolve => {
                        window.releaseHeldState=()=>resolve(response);
                        window.evofitHeldStateReady=true;
                    });
                };
            }''')
            target='all' if tab.locator('[data-ranking-period="month"]').get_attribute('aria-pressed')=='true' else 'month'
            tab.locator(f'[data-ranking-period="{target}"]').click()
            tab.wait_for_function('window.evofitHeldStateReady===true')
            assert tab.evaluate('window.evofitHeldStateUser')==student_id, 'The delayed response did not belong to the original account'

        def release_ranking_refresh(tab):
            tab.evaluate('window.releaseHeldState()')
            # The marker runs in the next task after JSON consumption and refresh callbacks.
            tab.wait_for_function('window.evofitHeldStateConsumed===true')

        try:
            login(page, student_email, 'aluno')
            assert page.evaluate("dayKey(parseDate('2026-11-01'))")=='2026-10-31', 'Date-only values no longer match PHP UTC midnight in São Paulo'
            for hidden_tab in ['Alimentação', 'Evolução', 'Perfil']:
                expect(page.locator('nav').get_by_role('button', name=hidden_tab, exact=True)).to_have_count(0)
            metric(page, 'completed', str(initial_workouts))
            metric(page, 'days', '1')
            metric(page, 'exercises', '2')
            metric(page, 'load', '20')
            page.get_by_role('button', name='Últimos 7 dias', exact=True).click()
            expect(page.locator('[data-days="7"]')).to_have_attribute('aria-pressed', 'true')
            metric(page, 'completed', str(initial_workouts))
            page.get_by_role('button', name='Últimos 30 dias', exact=True).click()
            expect(page.locator('[data-days="30"]')).to_have_attribute('aria-pressed', 'true')
            metric(page, 'completed', str(initial_workouts))
            metric(page, 'days', '1')
            metric(page, 'exercises', '2')
            metric(page, 'load', '20')
            capture(page, 'EvoFit-Focus-dashboard.png')
            nav(page, 'Treinos')
            expect(page.locator('.workout-dots button')).to_have_count(4)
            expect(page.get_by_role('button', name='Treino anterior', exact=True)).to_be_disabled()
            page.get_by_role('button', name='Próximo treino', exact=True).click()
            expect(page.locator('.workout-active h2')).to_have_text('Superior I')
            page.get_by_role('button', name='Treino anterior', exact=True).click()
            expect(page.locator('.workout-active h2')).to_have_text('Posterior / Glúteo')
            page.locator('[data-workout-carousel]').focus()
            page.keyboard.press('End')
            expect(page.locator('.workout-active h2')).to_have_text('Superior II')
            expect(page.get_by_role('button', name='Próximo treino', exact=True)).to_be_disabled()
            page.keyboard.press('Home')
            expect(page.locator('.workout-active h2')).to_have_text('Posterior / Glúteo')
            choose_workout(page, 'Quadríceps', open_details=False)
            capture(page, 'EvoFit-Focus-treinos.png')
            choose_workout(page, 'Quadríceps')
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
            capture(page, 'EvoFit-PHP-exercicio.png')
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
            choose_workout(page, 'Quadríceps')
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
            choose_workout(personal, 'Quadríceps')
            expect(personal.locator('.workout-progress strong')).to_contain_text('1')
            expect(personal.locator('[data-complete-exercise]')).to_have_count(0)
            other = page.locator('details').nth(1)
            other.locator('summary').click()
            other.get_by_role('button', name='Concluir exercício', exact=False).click()
            expect(page.get_by_role('button', name='Concluir treino', exact=False)).to_be_enabled()
            page.get_by_label('Observações do treino', exact=True).fill('Treino completo com PHP e MySQL')
            page.get_by_role('button', name='Concluir treino', exact=False).click()
            assert_completed_history(page)
            personal.reload()
            personal.locator('nav').wait_for()
            nav(personal, 'Histórico')
            assert_completed_history(personal)
            nav(page, 'Painel')
            metric(page, 'completed', str(initial_workouts+1))
            metric(page, 'exercises', '4')
            metric(page, 'load', re.compile(r'27[,.]5'))
            nav(page, 'Ranking')
            page.get_by_role('button', name='Ranking deste mês', exact=True).click()
            expect(page.locator('[data-ranking-period="month"]')).to_have_attribute('aria-pressed', 'true')
            assert_team_ranking(page, 'month')
            page.get_by_role('button', name='Ranking geral', exact=True).click()
            expect(page.locator('[data-ranking-period="all"]')).to_have_attribute('aria-pressed', 'true')
            assert_team_ranking(page, 'all')
            page.evaluate("document.querySelector('#toast').style.display='none'")
            capture(page, 'EvoFit-Focus-ranking.png')
            # Personal creates/edits plans through existing forms with PHP persistence.
            nav(personal, 'Treinos')
            choose_workout(personal, 'Quadríceps', open_details=False)
            personal.locator('.workout-active').get_by_role('button', name='Editar treino').click()
            personal.locator('.editor').first.get_by_label('Imagem do exercício').select_option('extension')
            personal.locator('.editor').first.get_by_label('Instruções / observações').fill('Mantenha as costas apoiadas e controle a descida.')
            personal.get_by_label('Título / dia / divisão').fill('Quadríceps atualizado')
            personal.get_by_role('button', name='Salvar e atribuir').click()
            expect(personal.locator('.workout-selector')).to_be_visible()
            fixture['plans']['Quadríceps atualizado']=fixture['plans']['Quadríceps']
            nav(personal, 'Alunos')
            addition=personal.locator('#addstudent')
            new_email=f'focus-davi-{uuid.uuid4().hex}@example.com'
            addition.locator('[name="name"]').fill('Davi Santos')
            addition.locator('[name="email"]').fill(new_email)
            addition.locator('[name="password"]').fill('Teste123!')
            addition.locator('[name="goal"]').fill('Ganhar força')
            addition.locator('button').last.click()
            expect(personal.locator('#content')).to_contain_text('Davi Santos')
            added=next(person for person in trainer_api.request('state')['students'] if person['email']==new_email)
            assert added['name']=='Davi Santos', 'Personal student form did not persist'
            ApiClient(base).login(new_email,'aluno','Teste123!')
            page.reload()
            page.locator('nav').wait_for()
            nav(page, 'Treinos')
            expect(page.locator('.workout-selector')).to_be_visible()
            choose_workout(page, 'Quadríceps atualizado')
            page.locator('details').first.locator('summary').click()
            page.evaluate("document.querySelector('#toast').style.display='none'")
            capture(page, 'EvoFit-PHP-exercicio.png')
            page.get_by_role('button', name='Todos os treinos', exact=False).click()
            page.set_viewport_size(dict(width=375, height=812))
            page.emulate_media(reduced_motion='reduce')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile cards overflow'
            choose_workout(page, 'Quadríceps atualizado')
            if not page.locator('details').first.evaluate('(el)=>el.open'):
                page.locator('details').first.locator('summary').click()
            page.evaluate("document.querySelector('#toast').style.display='none'")
            capture(page, 'EvoFit-Focus-mobile-exercicio.png')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile exercise overflow'
            page.locator('details').first.locator('summary').focus()
            page.keyboard.press('Enter')
            assert not page.locator('details').first.evaluate('(el)=>el.open'), 'Keyboard toggle did not close the exercise'
            nav(page, 'Painel')
            metric(page, 'completed', str(initial_workouts+1))
            assert page.locator('.focus-hero').evaluate('''hero => {
                const h=hero.getBoundingClientRect(),b=hero.querySelector('button').getBoundingClientRect();
                return b.top>=h.top && b.bottom<=h.bottom && b.left>=h.left && b.right<=h.right;
            }'''), 'Mobile hero training button is clipped'
            page.evaluate("document.querySelector('#toast').style.display='none'")
            capture(page, 'EvoFit-Focus-mobile.png', full_page=False)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile dashboard overflow'
            nav(page, 'Ranking')
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile ranking overflow'
            assert page.evaluate("matchMedia('(prefers-reduced-motion: reduce)').matches"), 'Reduced-motion emulation failed'
            assert len(student_api.request('state')['logs']) == initial_workouts+1, 'Completed workout was not persisted once'
            # A state request already received from the server must not revive a logged-out UI.
            hold_ranking_refresh(page)
            page.get_by_role('button', name='Sair da conta', exact=True).click()
            expect(page.locator('#auth')).to_be_visible()
            release_ranking_refresh(page)
            expect(page.locator('#auth')).to_be_visible()
            expect(page.locator('nav')).to_have_count(0)
            # The same delayed response must not replace a later account or reveal the old team.
            login(page, student_email, 'aluno')
            nav(page, 'Ranking')
            hold_ranking_refresh(page)
            page.get_by_role('button', name='Sair da conta', exact=True).click()
            expect(page.locator('#auth')).to_be_visible()
            login(page, fixture['outside_email'], 'aluno', navigate=False)
            expect(page.locator('.user-chip strong')).to_have_text('Fora da equipe')
            nav(page, 'Ranking')
            expect(page.locator('.ranking-unlinked')).to_be_visible()
            release_ranking_refresh(page)
            expect(page.locator('.user-chip strong')).to_have_text('Fora da equipe')
            expect(page.locator('.ranking-unlinked')).to_be_visible()
            expect(page.locator('[data-ranking-student]')).to_have_count(0)
            expect(page.locator('#content')).not_to_contain_text('TEAM LIVIA FOCO FOCUS')
            assert not errors, errors
            assert not bad_responses, bad_responses
            print('PASS: training dashboard filters, card carousel and keyboard, exercises/images/loads, saved resume/history, own-team ranking, personal forms, mobile375px/reducedmotion, date-only UTC alignment, held-state logout/cross-account isolation and no JavaScript errors.')
        finally:
            student_context.close()
            trainer_context.close()
            browser.close()


if __name__ == '__main__':
    run()
