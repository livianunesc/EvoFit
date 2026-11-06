// Treinos: cards, detalhes e progresso persistido por exercício.
let selectedWorkout = null;
let exerciseDrafts = {};
let workoutNotes = {};
let expandedExercises = new Set();
let savingExercise = false;
let featuredWorkoutByContext = new Map();
let workoutTouchStart = null;

const exerciseIllustrations = [
  ['auto', 'Automática pelo nome'], ['extension', 'Cadeira extensora'],
  ['squat', 'Agachamento'], ['leg-press', 'Leg press'], ['row', 'Remada'],
  ['posterior', 'Posterior / glúteo'], ['upper', 'Superiores'],
  ['quadriceps', 'Quadríceps'], ['generic', 'Exercício geral']
];
function resetWorkouts() {
  selectedWorkout = null; exerciseDrafts = {}; workoutNotes = {};
  expandedExercises = new Set(); savingExercise = false;
  featuredWorkoutByContext = new Map(); workoutTouchStart = null;
}
function normalizedName(name) {
  return String(name || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
}
function illustrationFor(item) {
  if (item.illustration && item.illustration !== 'auto' && exerciseIllustrations.some(([key]) => key === item.illustration)) return item.illustration;
  const name = normalizedName(item.name);
  if (/extensor/.test(name)) return 'extension';
  if (/leg.?press/.test(name)) return 'leg-press';
  if (/agach|squat/.test(name)) return 'squat';
  if (/remada/.test(name)) return 'row';
  if (/glute|posterior|stiff|flexora/.test(name)) return 'posterior';
  if (/supino|superior|peito|biceps|triceps|ombro/.test(name)) return 'upper';
  if (/quadric/.test(name)) return 'quadriceps';
  return 'generic';
}
function coverFor(plan) {
  const name = normalizedName(plan.title);
  if (/posterior|glute/.test(name)) return 'posterior';
  if (/quadric/.test(name)) return 'quadriceps';
  if (/superior|peito|costa|braco/.test(name)) return 'upper';
  return illustrationFor(plan.items[0] || {});
}
function progressFor(plan) {
  return (state.workoutProgress || []).find(p => p.student === +student && p.plan === plan.id);
}
function exerciseKey(plan, index) { return `${state.user.id}:${plan.id}:${index}`; }
function exerciseValue(plan, index) {
  const saved = progressFor(plan)?.exercises[index];
  const key = exerciseKey(plan, index);
  return {load: exerciseDrafts[key] ?? saved?.load ?? plan.items[index].load, done: saved?.done === true};
}
function workoutArrow(direction = 'right') {
  return `<svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="${direction === 'left' ? 'M19 12H5m0 0 6 6m-6-6 6-6' : 'M5 12h14m0 0-6-6m6 6-6 6'}" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`;
}
function workoutContext() { return `${state.user.id}:${student}`; }
function featuredWorkoutIndex(list) {
  const id = featuredWorkoutByContext.get(workoutContext());
  return Math.max(0, list.findIndex(plan => plan.id === id));
}
function featureWorkout(id, focusSelector = '[data-workout-carousel]') {
  const list = plans('workout');
  if (!list.some(plan => plan.id === id)) return;
  featuredWorkoutByContext.set(workoutContext(), id);
  updateWorkoutContent(focusSelector);
}
function moveFeaturedWorkout(direction) {
  const list = plans('workout');
  const current = featuredWorkoutIndex(list);
  const next = Math.min(list.length - 1, Math.max(0, current + direction));
  if (list[next] && next !== current) featureWorkout(list[next].id);
}
function workoutProductCard(plan, position, index) {
  const active = position === 'active';
  const saved = progressFor(plan);
  const completed = saved?.exercises.filter(e => e.done).length || 0;
  const count = plan.items.length;
  return `<article class="workout-tile workout-${position}" aria-label="${active ? 'Treino selecionado: ' : ''}${esc(plan.title)}"><div class="workout-card${active ? ' is-featured' : ''}"><span class="workout-card-index" aria-hidden="true">${String(index + 1).padStart(2, '0')}</span><figure class="workout-product-art"><img src="images/${coverFor(plan)}.svg" alt="Ilustração de ${esc(plan.title)}" ${active ? 'fetchpriority="high"' : 'loading="lazy"'}></figure><div class="workout-product-copy"><span class="workout-category">${completed ? 'Sua evolução continua' : 'Força. Foco. Evolução.'}</span><h2>${esc(plan.title)}</h2><div class="workout-product-meta"><span>${count} ${count === 1 ? 'exercício' : 'exercícios'}</span><span>${completed ? `${completed}/${count} concluídos` : 'No seu ritmo'}</span></div>${active ? `<p class="workout-product-description">${personal() ? 'Consulte a divisão, acompanhe as cargas e a evolução do aluno.' : completed ? 'Seu progresso está salvo. Continue de onde parou e complete mais uma conquista.' : 'Um exercício de cada vez. Abra seu treino e dê o próximo passo.'}</p><button type="button" class="workout-start" data-open-workout="${plan.id}">${personal() ? 'VER EXERCÍCIOS' : completed ? 'RETOMAR TREINO' : 'INICIAR TREINO'} ${workoutArrow()}</button>${personal() ? `<button type="button" class="workout-edit" data-edit="${plan.id}">Editar treino</button>` : ''}` : `<span class="workout-preview-label">SELECIONAR TREINO ${workoutArrow()}</span>`}</div>${!active ? `<button type="button" class="workout-feature-select" data-feature-workout="${plan.id}" aria-label="Selecionar treino: ${esc(plan.title)}"></button>` : ''}</div></article>`;
}
function workoutSection() {
  const list = plans('workout');
  const toolbar = personal() ? `<div class="workout-toolbar"><button class="btn" data-new="workout">+ Novo treino</button><p class="hint">Crie uma divisão e atribua os exercícios ao aluno selecionado.</p></div>` : '';
  if (editing) return `${toolbar}${editor(editing)}`;
  const plan = list.find(p => p.id === selectedWorkout);
  if (plan) return `${toolbar}${workoutDetails(plan)}`;
  if (!list.length) return `${toolbar}<section class="workout-empty"><span class="workout-empty-mark" aria-hidden="true">↗</span><span class="eyebrow">O PRÓXIMO PASSO COMEÇA AQUI</span><h2>Seu treino vai ganhar espaço.</h2><p>${personal() ? 'Crie o primeiro treino para este aluno. Cada divisão se transforma em um card e cada exercício tem seu próprio acompanhamento.' : 'Assim que seu personal atribuir uma divisão, ela aparecerá aqui, pronta para começar.'}</p>${personal() ? '<button class="btn" data-new="workout">Criar primeiro treino</button>' : ''}</section>`;
  const current = featuredWorkoutIndex(list);
  const featured = list[current];
  const dots = list.map((p, i) => `<button type="button" class="workout-dot${i === current ? ' is-current' : ''}" data-feature-workout="${p.id}" aria-label="Selecionar treino ${i + 1}: ${esc(p.title)}" ${i === current ? 'aria-current="true"' : ''}><span></span></button>`).join('');
  return `${toolbar}<section class="workout-selector" aria-label="Escolher treino"><header class="workout-selector-heading"><span class="eyebrow">FEITO PARA O SEU PRÓXIMO NÍVEL</span><h2>ESCOLHA SEU <em>DESAFIO.</em></h2><p>${personal() ? 'Cada aluno tem seu ritmo. Cada treino, um objetivo.' : 'Seu objetivo está à frente. Qual vai ser o treino de hoje?'}</p></header><div class="workout-stage" data-workout-carousel tabindex="0" role="region" aria-roledescription="carrossel" aria-label="Treinos. Use as setas para escolher." data-count="${list.length}">${list[current - 1] ? workoutProductCard(list[current - 1], 'previous', current - 1) : '<div class="workout-spacer" aria-hidden="true"></div>'}${workoutProductCard(featured, 'active', current)}${list[current + 1] ? workoutProductCard(list[current + 1], 'next', current + 1) : '<div class="workout-spacer" aria-hidden="true"></div>'}</div><footer class="workout-selector-footer"><div class="workout-carousel-controls"><button type="button" class="workout-nav" data-workout-direction="-1" aria-label="Treino anterior" ${current === 0 ? 'disabled' : ''}>${workoutArrow('left')}</button><span class="workout-position" aria-live="polite" aria-atomic="true"><strong>${String(current + 1).padStart(2, '0')}</strong><span>/ ${String(list.length).padStart(2, '0')}</span><span class="sr-only"> · ${esc(featured.title)}</span></span><button type="button" class="workout-nav" data-workout-direction="1" aria-label="Próximo treino" ${current === list.length - 1 ? 'disabled' : ''}>${workoutArrow()}</button></div><div class="workout-dots" aria-label="Selecionar divisão de treino">${dots}</div><span class="workout-selector-hint">${list.length > 1 ? 'ESCOLHA. COMECE. EVOLUA.' : 'SEU PRÓXIMO PASSO ESTÁ AQUI.'}</span></footer></section>`;
}
function workoutDetails(plan) {
  const progress = progressFor(plan);
  const completed = progress?.exercises.filter(x => x.done).length || 0;
  const allDone = plan.items.length > 0 && completed === plan.items.length;
  return `<div class="workout-breadcrumb"><button type="button" class="outline workout-back" data-back-workouts>${workoutArrow('left')} Todos os treinos</button><span class="muted">${esc(plan.title)}</span></div><section class="workout-heading"><div><span class="eyebrow">${personal() ? 'ACOMPANHAMENTO DO ALUNO' : 'MODO TREINO · VOCÊ NO CONTROLE'}</span><h2>${esc(plan.title)}</h2><p class="muted">Toque no nome de um exercício para abrir os detalhes.</p></div><div class="workout-progress" role="status"><strong>${completed}<span> / ${plan.items.length}</span></strong><span>exercícios concluídos</span><progress value="${completed}" max="${Math.max(1, plan.items.length)}" aria-label="Exercícios concluídos"></progress></div></section><div class="exercise-list">${plan.items.map((item, i) => exerciseDetails(plan, item, i)).join('')}</div>${!personal() ? `<section class="card workout-finish"><span class="eyebrow">MAIS PERTO DO SEU OBJETIVO</span><h2>O último passo é seu.</h2><label>Observações do treino<textarea id="workout-notes" data-notes-plan="${plan.id}" placeholder="Como você se sentiu hoje?">${esc(workoutNotes[plan.id] || '')}</textarea></label><div class="row"><p class="muted">${allDone ? 'Todos os exercícios concluídos. Salve o treino no seu histórico!' : 'Conclua cada exercício acima para liberar a finalização do treino.'}</p><button class="workout-finish-button" data-finish-workout="${plan.id}" ${allDone ? '' : 'disabled'}>Concluir treino ✓</button></div><p class="hint">Cada exercício concluído fica salvo. Você pode sair e retomar depois.</p></section>` : `<p class="hint">O aluno registra as cargas e conclui os exercícios pela conta dele. Atualize a página para consultar novos registros.</p>`}`;
}
function exerciseDetails(plan, item, index) {
  const value = exerciseValue(plan, index);
  const key = exerciseKey(plan, index);
  const previous = logs('workout').flatMap(log => log.data.exercises || []).filter(x => x.name === item.name).at(-1);
  return `<details class="exercise-accordion ${value.done ? 'is-complete' : ''}" data-exercise-key="${key}" ${expandedExercises.has(key) ? 'open' : ''}><summary><span class="exercise-number">${value.done ? '✓' : String(index + 1).padStart(2, '0')}</span><span class="exercise-summary"><strong>${esc(item.name)}</strong><small>${esc(item.sets)} séries · ${esc(item.reps)} repetições</small></span><span class="exercise-status">${value.done ? 'Concluído' : 'Ver exercício'}</span><span class="accordion-chevron" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="m6 9 6 6 6-6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span></summary><div class="exercise-detail-body"><figure class="exercise-figure"><img src="images/${illustrationFor(item)}.svg" alt="Ilustração de referência: ${esc(item.name)}" loading="lazy"><figcaption>Ilustração de referência · siga as orientações do seu personal.</figcaption></figure><section class="exercise-description" aria-label="Descrição de ${esc(item.name)}"><span class="eyebrow">DESCRIÇÃO DO EXERCÍCIO</span><h3>${esc(item.name)}</h3><div class="exercise-metrics"><div><span>Séries</span><strong>${esc(item.sets)}</strong></div><div><span>Repetições</span><strong>${esc(item.reps)}</strong></div><div><span>Descanso</span><strong>${esc(item.rest)} <small>s</small></strong></div></div><p class="exercise-instructions">${esc(item.notes || 'Execute de forma controlada, respeitando a amplitude orientada pelo seu personal.')}</p><div class="exercise-load">${personal()?'<span class="load-label">Carga registrada (kg)</span>':`<label for="load-${plan.id}-${index}">Carga utilizada (kg)</label>`}${personal() ? `<strong id="load-${plan.id}-${index}" class="trainer-load">${esc(value.load)} kg</strong>` : `<div class="load-stepper"><button type="button" class="outline" aria-label="Diminuir carga de ${esc(item.name)}" data-load-step="-0.5" data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}>−</button><input id="load-${plan.id}-${index}" type="number" aria-label="Carga utilizada em ${esc(item.name)} (kg)" min="0" max="1999.5" step="0.5" value="${esc(value.load)}" data-exercise-load data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}><button type="button" class="outline" aria-label="Aumentar carga de ${esc(item.name)}" data-load-step="0.5" data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}>+</button></div>`}<p class="hint">Carga indicada: ${esc(item.load)} kg${previous ? ` · Último registro: ${esc(previous.load)} kg` : ''}</p></div>${!personal() ? `<div class="exercise-completion"><button type="button" data-complete-exercise="${index}" data-plan="${plan.id}" ${value.done ? 'disabled' : ''}>${value.done ? '✓ Exercício concluído' : 'Concluir exercício ✓'}</button>${value.done ? `<button class="outline" type="button" data-reopen-exercise="${index}" data-plan="${plan.id}">Ajustar carga</button>` : ''}</div>` : `<span class="tag">${value.done ? '✓ Concluído pelo aluno' : 'Aguardando o aluno'}</span>`}</section></div></details>`;
}
function updateWorkoutContent(focusSelector) {
  document.querySelector('#content').innerHTML = workoutSection();
  if (focusSelector) document.querySelector(focusSelector)?.focus({preventScroll: true});
}
function setProgress(progress) {
  state.workoutProgress = (state.workoutProgress || []).filter(p => !(p.plan === progress.plan && p.student === progress.student));
  state.workoutProgress.push(progress);
}
async function handleWorkoutClick(e, b) {
  if (b.hasAttribute('data-feature-workout')) { featureWorkout(+b.dataset.featureWorkout); return true; }
  if (b.hasAttribute('data-workout-direction')) { moveFeaturedWorkout(+b.dataset.workoutDirection); return true; }
  if (b.hasAttribute('data-open-workout')) {
    selectedWorkout = +b.dataset.openWorkout; featuredWorkoutByContext.set(workoutContext(), selectedWorkout); editing = null; tab = 'Treinos'; render();
    document.querySelector('.workout-heading h2')?.setAttribute('tabindex', '-1');
    document.querySelector('.workout-heading h2')?.focus();
    return true;
  }
  if (b.hasAttribute('data-back-workouts')) {const previous=selectedWorkout; selectedWorkout = null; updateWorkoutContent(`[data-open-workout="${previous}"]`); return true;}
  if (b.hasAttribute('data-load-step')) {
    const plan = state.plans.find(p => p.id === +b.dataset.plan);
    const index = +b.dataset.index;
    const input = document.querySelector(`#load-${plan.id}-${index}`);
    if (input.disabled) return true;
    const current = Number(input.value);
    input.value = Math.min(1999.5, Math.max(0, (Number.isFinite(current) ? current : 0) + Number(b.dataset.loadStep)));
    exerciseDrafts[exerciseKey(plan, index)] = input.value;
    return true;
  }
  const isComplete = b.hasAttribute('data-complete-exercise');
  const isReopen = b.hasAttribute('data-reopen-exercise');
  if (isComplete || isReopen) {
    if (savingExercise) return true;
    const plan = state.plans.find(p => p.id === +b.dataset.plan);
    const index = +(isComplete ? b.dataset.completeExercise : b.dataset.reopenExercise);
    const input = document.querySelector(`#load-${plan.id}-${index}`);
    if (!input || !input.checkValidity() || input.value === '') {input?.reportValidity(); toast('Informe uma carga válida, em kg.'); return true;}
    const context=captureAuth();
    savingExercise = true;
    const controlStates = [...b.closest('details').querySelectorAll('input,button')].map(control => [control,control.disabled]);
    controlStates.forEach(([control]) => control.disabled=true);
    const title = b.textContent; b.textContent = 'Salvando…';
    try {
      const result = await api('exercise', {plan: plan.id, version: plan.version, index, load: Number(input.value), done: isComplete, session: progressFor(plan)?.session});
      if(!isAuthCurrent(context))return true;
      setProgress(result.progress); delete exerciseDrafts[exerciseKey(plan, index)];
      toast(isComplete ? 'Exercício concluído e salvo!' : 'Carga liberada para edição.');
      if (tab === 'Treinos' && selectedWorkout === plan.id) updateWorkoutContent(isReopen ? `#load-${plan.id}-${index}` : `details[data-exercise-key="${exerciseKey(plan,index)}"] summary`);
    } catch (err) {if(isAuthCurrent(context))await resolveWorkoutError(err, plan);} finally {if(isAuthCurrent(context))savingExercise = false; controlStates.forEach(([control,disabled]) => control.disabled=disabled); b.textContent = title;}
    return true;
  }
  if (b.hasAttribute('data-finish-workout')) {
    const plan = state.plans.find(p => p.id === +b.dataset.finishWorkout);
    const progress = progressFor(plan);
    if (!progress || !progress.exercises.every(x => x.done)) {toast('Conclua todos os exercícios primeiro.'); return true;}
    const context=captureAuth();
    b.disabled = true; b.textContent = 'Salvando treino…';
    try {
      await api('workout/complete', {plan: plan.id, session: progress.session, notes: workoutNotes[plan.id] || ''});
      if(!isAuthCurrent(context))return true;
      delete workoutNotes[plan.id];
      plan.items.forEach((_, i) => {delete exerciseDrafts[exerciseKey(plan, i)]; expandedExercises.delete(exerciseKey(plan, i));});
      selectedWorkout = null; tab = 'Histórico';
      await refresh(); if(!isAuthCurrent(context))return true; if (typeof celebrateWorkout === 'function') celebrateWorkout(); toast('Treino concluído! Seu histórico e o painel do personal foram atualizados.');
    } catch (err) {if(isAuthCurrent(context))await resolveWorkoutError(err, plan); b.disabled = false; b.textContent = 'Concluir treino ✓';}
    return true;
  }
  return false;
}

async function resolveWorkoutError(err, plan) {
  const context=captureAuth();
  if (err.status === 409) {
    plan.items.forEach((_, i) => {delete exerciseDrafts[exerciseKey(plan, i)]; expandedExercises.delete(exerciseKey(plan, i));});
    await refresh();
  }
  if(isAuthCurrent(context))toast(err.message);
}

// Carousel controls remain available to keyboard and touch users without auto-rotation.
document.addEventListener('keydown', event => {
  if (typeof state === 'undefined' || !state || tab !== 'Treinos' || selectedWorkout !== null || editing) return;
  if (!event.target.closest('.workout-selector') || event.target.matches('input,textarea,select')) return;
  const list = plans('workout');
  if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
    event.preventDefault(); moveFeaturedWorkout(event.key === 'ArrowLeft' ? -1 : 1);
  } else if (event.key === 'Home' || event.key === 'End') {
    event.preventDefault(); if (list.length) featureWorkout(list[event.key === 'Home' ? 0 : list.length - 1].id);
  }
});
document.addEventListener('touchstart', event => {
  if (!event.target.closest('[data-workout-carousel]') || event.touches.length !== 1) return;
  workoutTouchStart = {x: event.touches[0].clientX, y: event.touches[0].clientY};
}, {passive: true});
document.addEventListener('touchend', event => {
  const start = workoutTouchStart; workoutTouchStart = null;
  if (!start || typeof state === 'undefined' || !state || tab !== 'Treinos' || selectedWorkout !== null || editing || !event.changedTouches.length) return;
  const dx = event.changedTouches[0].clientX - start.x;
  const dy = event.changedTouches[0].clientY - start.y;
  if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.4) moveFeaturedWorkout(dx < 0 ? 1 : -1);
}, {passive: true});
