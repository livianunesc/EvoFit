// Treinos: cards, detalhes e progresso persistido por exercício.
let selectedWorkout = null;
let exerciseDrafts = {};
let workoutNotes = {};
let expandedExercises = new Set();
let savingExercise = false;

const exerciseIllustrations = [
  ['auto', 'Automática pelo nome'], ['extension', 'Cadeira extensora'],
  ['squat', 'Agachamento'], ['leg-press', 'Leg press'], ['row', 'Remada'],
  ['posterior', 'Posterior / glúteo'], ['upper', 'Superiores'],
  ['quadriceps', 'Quadríceps'], ['generic', 'Exercício geral']
];
function resetWorkouts() {
  selectedWorkout = null; exerciseDrafts = {}; workoutNotes = {};
  expandedExercises = new Set(); savingExercise = false;
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
function workoutSection() {
  const list = plans('workout');
  const toolbar = personal() ? `<div class="workout-toolbar"><button data-new="workout">+ Novo treino</button><p class="hint">Crie uma divisão para cada card e atribua os exercícios ao aluno selecionado.</p></div>` : '';
  if (editing) return `${toolbar}${editor(editing)}`;
  const plan = list.find(p => p.id === selectedWorkout);
  if (plan) return `${toolbar}${workoutDetails(plan)}`;
  return `${toolbar}<div class="workout-intro"><span class="eyebrow">SUA ROTINA, UM TREINO POR VEZ</span><p class="muted">${personal() ? 'Abra um card para consultar os exercícios e acompanhar as conclusões do aluno.' : 'Escolha seu treino. Depois, toque em cada exercício para ver como fazer e registrar sua carga.'}</p></div><div class="workout-grid">${list.map(plan => {
    const progress = progressFor(plan);
    const done = progress?.exercises.filter(e => e.done).length || 0;
    const cover = coverFor(plan);
    return `<article class="workout-tile"><button class="workout-card" data-open-workout="${plan.id}" aria-label="${personal() ? 'Ver' : done ? 'Retomar' : 'Iniciar'} treino: ${esc(plan.title)}"><span class="workout-card-top"><span class="tag">${plan.items.length} ${plan.items.length === 1 ? 'exercício' : 'exercícios'}</span>${done ? `<span class="workout-resume">${done}/${plan.items.length} concluídos</span>` : '<span class="workout-arrow" aria-hidden="true">↗</span>'}</span><h2>${esc(plan.title)}</h2><div class="workout-cover"><img src="/images/${cover}.svg" alt="Ilustração de ${esc(plan.title)}" loading="lazy"></div><span class="workout-card-bottom">${personal() ? 'VER EXERCÍCIOS' : done ? 'RETOMAR TREINO' : 'INICIAR TREINO'} <span aria-hidden="true">→</span></span></button>${personal() ? `<button class="workout-edit outline" data-edit="${plan.id}">Editar treino</button>` : ''}</article>`;
  }).join('')}</div>${!list.length ? empty('Nenhum treino atribuído ainda. Seu personal pode criar uma divisão e os exercícios aparecerão aqui.') : ''}`;
}
function workoutDetails(plan) {
  const progress = progressFor(plan);
  const completed = progress?.exercises.filter(x => x.done).length || 0;
  const allDone = plan.items.length > 0 && completed === plan.items.length;
  return `<div class="workout-breadcrumb"><button class="outline" data-back-workouts>← Todos os treinos</button><span class="muted">${esc(plan.title)}</span></div><section class="workout-heading"><div><span class="eyebrow">${personal() ? 'ACOMPANHAMENTO DO ALUNO' : 'SEU TREINO DE HOJE'}</span><h2>${esc(plan.title)}</h2><p class="muted">Toque no nome de um exercício para abrir os detalhes.</p></div><div class="workout-progress" role="status"><strong>${completed}<span> / ${plan.items.length}</span></strong><span>exercícios concluídos</span><progress value="${completed}" max="${Math.max(1, plan.items.length)}" aria-label="Exercícios concluídos"></progress></div></section><div class="exercise-list">${plan.items.map((item, i) => exerciseDetails(plan, item, i)).join('')}</div>${!personal() ? `<section class="card workout-finish"><h2>Finalize sua conquista</h2><label>Observações do treino<textarea id="workout-notes" data-notes-plan="${plan.id}" placeholder="Como você se sentiu hoje?">${esc(workoutNotes[plan.id] || '')}</textarea></label><div class="row"><p class="muted">${allDone ? 'Todos os exercícios concluídos. Salve o treino no seu histórico!' : 'Conclua cada exercício acima para liberar a finalização do treino.'}</p><button data-finish-workout="${plan.id}" ${allDone ? '' : 'disabled'}>Concluir treino ✓</button></div><p class="hint">Cada exercício concluído fica salvo. Você pode sair e retomar depois.</p></section>` : `<p class="hint">O aluno registra as cargas e conclui os exercícios pela conta dele. Atualize a página para consultar novos registros.</p>`}`;
}
function exerciseDetails(plan, item, index) {
  const value = exerciseValue(plan, index);
  const key = exerciseKey(plan, index);
  const previous = logs('workout').flatMap(log => log.data.exercises || []).filter(x => x.name === item.name).at(-1);
  return `<details class="exercise-accordion ${value.done ? 'is-complete' : ''}" data-exercise-key="${key}" ${expandedExercises.has(key) ? 'open' : ''}><summary><span class="exercise-number">${value.done ? '✓' : String(index + 1).padStart(2, '0')}</span><span class="exercise-summary"><strong>${esc(item.name)}</strong><small>${esc(item.sets)} séries · ${esc(item.reps)} repetições</small></span><span class="exercise-status">${value.done ? 'Concluído' : 'Ver exercício'}</span><span class="accordion-chevron" aria-hidden="true">⌄</span></summary><div class="exercise-detail-body"><figure class="exercise-figure"><img src="/images/${illustrationFor(item)}.svg" alt="Ilustração de referência: ${esc(item.name)}" loading="lazy"><figcaption>Ilustração de referência · siga as orientações do seu personal.</figcaption></figure><section class="exercise-description" aria-label="Descrição de ${esc(item.name)}"><span class="eyebrow">DESCRIÇÃO DO EXERCÍCIO</span><h3>${esc(item.name)}</h3><div class="exercise-metrics"><div><span>Séries</span><strong>${esc(item.sets)}</strong></div><div><span>Repetições</span><strong>${esc(item.reps)}</strong></div><div><span>Descanso</span><strong>${esc(item.rest)} <small>s</small></strong></div></div><p class="exercise-instructions">${esc(item.notes || 'Execute de forma controlada, respeitando a amplitude orientada pelo seu personal.')}</p><div class="exercise-load">${personal()?'<span class="load-label">Carga registrada (kg)</span>':`<label for="load-${plan.id}-${index}">Carga utilizada (kg)</label>`}${personal() ? `<strong id="load-${plan.id}-${index}" class="trainer-load">${esc(value.load)} kg</strong>` : `<div class="load-stepper"><button type="button" class="outline" aria-label="Diminuir carga de ${esc(item.name)}" data-load-step="-0.5" data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}>−</button><input id="load-${plan.id}-${index}" type="number" aria-label="Carga utilizada em ${esc(item.name)} (kg)" min="0" max="1999.5" step="0.5" value="${esc(value.load)}" data-exercise-load data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}><button type="button" class="outline" aria-label="Aumentar carga de ${esc(item.name)}" data-load-step="0.5" data-plan="${plan.id}" data-index="${index}" ${value.done ? 'disabled' : ''}>+</button></div>`}<p class="hint">Carga indicada: ${esc(item.load)} kg${previous ? ` · Último registro: ${esc(previous.load)} kg` : ''}</p></div>${!personal() ? `<div class="exercise-completion"><button type="button" data-complete-exercise="${index}" data-plan="${plan.id}" ${value.done ? 'disabled' : ''}>${value.done ? '✓ Exercício concluído' : 'Concluir exercício ✓'}</button>${value.done ? `<button class="outline" type="button" data-reopen-exercise="${index}" data-plan="${plan.id}">Ajustar carga</button>` : ''}</div>` : `<span class="tag">${value.done ? '✓ Concluído pelo aluno' : 'Aguardando o aluno'}</span>`}</section></div></details>`;
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
  if (b.hasAttribute('data-open-workout')) {
    selectedWorkout = +b.dataset.openWorkout; editing = null; tab = 'Treinos'; render();
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
    savingExercise = true;
    const controlStates = [...b.closest('details').querySelectorAll('input,button')].map(control => [control,control.disabled]);
    controlStates.forEach(([control]) => control.disabled=true);
    const title = b.textContent; b.textContent = 'Salvando…';
    try {
      const result = await api('exercise', {plan: plan.id, version: plan.version, index, load: Number(input.value), done: isComplete, session: progressFor(plan)?.session});
      setProgress(result.progress); delete exerciseDrafts[exerciseKey(plan, index)];
      toast(isComplete ? 'Exercício concluído e salvo!' : 'Carga liberada para edição.');
      if (tab === 'Treinos' && selectedWorkout === plan.id) updateWorkoutContent(isReopen ? `#load-${plan.id}-${index}` : `details[data-exercise-key="${exerciseKey(plan,index)}"] summary`);
    } catch (err) {await resolveWorkoutError(err, plan);} finally {savingExercise = false; controlStates.forEach(([control,disabled]) => control.disabled=disabled); b.textContent = title;}
    return true;
  }
  if (b.hasAttribute('data-finish-workout')) {
    const plan = state.plans.find(p => p.id === +b.dataset.finishWorkout);
    const progress = progressFor(plan);
    if (!progress || !progress.exercises.every(x => x.done)) {toast('Conclua todos os exercícios primeiro.'); return true;}
    b.disabled = true; b.textContent = 'Salvando treino…';
    try {
      await api('workout/complete', {plan: plan.id, session: progress.session, notes: workoutNotes[plan.id] || ''});
      delete workoutNotes[plan.id];
      plan.items.forEach((_, i) => {delete exerciseDrafts[exerciseKey(plan, i)]; expandedExercises.delete(exerciseKey(plan, i));});
      selectedWorkout = null; tab = 'Histórico';
      await refresh(); toast('Treino concluído! Seu histórico e o painel do personal foram atualizados.');
    } catch (err) {await resolveWorkoutError(err, plan); b.disabled = false; b.textContent = 'Concluir treino ✓';}
    return true;
  }
  return false;
}

async function resolveWorkoutError(err, plan) {
  if (err.status === 409) {
    plan.items.forEach((_, i) => {delete exerciseDrafts[exerciseKey(plan, i)]; expandedExercises.delete(exerciseKey(plan, i));});
    await refresh();
  }
  toast(err.message);
}
