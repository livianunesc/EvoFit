const app = document.querySelector('#app');
let state, tab = 'Painel', student, register = false, editing = null;
let dashboardDays = 7, rankingPeriod = 'month', toastTimeout;
let authEpoch = 0, authRequestPending = false, refreshRevision = 0;
function captureAuth() {return {epoch:authEpoch,user:state?.user.id};}
function isAuthCurrent(context) {return context.epoch===authEpoch && context.user===state?.user.id;}
const APP_TZ = 'America/Sao_Paulo';
const esc = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const field = (name, label, value='', type='text', extra='') => `<label>${label}<input name="${name}" type="${type}" value="${esc(value)}" ${extra}></label>`;
const personal = () => state.user.role === 'personal';
const plans = kind => state.plans.filter(plan => plan.student == student && plan.kind === kind);
const logs = kind => state.logs.filter(log => log.student == student && (!kind || log.kind === kind));
const initials = name => String(name || '?').trim().split(/\s+/).slice(0,2).map(part => part[0]).join('').toUpperCase();
function icon(name, cls='') {
  const shapes = {
    home:'<path d="m3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z"/>',
    workout:'<path d="m6 4 14 14M4 6l14 14M3 8l5-5M16 21l5-5M2 5l3-3M19 22l3-3"/>',
    trophy:'<path d="M8 3h8v6a4 4 0 0 1-8 0ZM8 5H4v3a4 4 0 0 0 4 4M16 5h4v3a4 4 0 0 1-4 4M12 13v6M8 21h8M9 19h6"/>',
    history:'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7M12 7v5l3 2"/>',
    users:'<circle cx="9" cy="7" r="3"/><path d="M3 21v-3a6 6 0 0 1 12 0v3M16 4a3 3 0 0 1 0 6M21 21v-3a6 6 0 0 0-4-5"/>',
    logout:'<path d="M9 4H4v16h5M13 8l4 4-4 4M8 12h13"/>',
    'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
    'arrow-left':'<path d="M20 12H4m6 6-6-6 6-6"/>',
    'arrow-up-right':'<path d="M6 18 18 6M6 6h12v12"/>',
    check:'<path d="m5 12 4 4L19 6"/>', plus:'<path d="M12 5v14M5 12h14"/>',minus:'<path d="M5 12h14"/>',
    calendar:'<rect x="3" y="5" width="18" height="16" rx="3"/><path d="M7 3v4M17 3v4M3 11h18M7 15h2M15 15h2"/>',
    bolt:'<path d="m14 2-9 12h6l-1 8 9-12h-6Z"/>',
    target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',
    refresh:'<path d="M20 7a9 9 0 0 0-15 0M20 3v5h-5M4 17a9 9 0 0 0 15 0M4 21v-5h5"/>',
    close:'<path d="m6 6 12 12M18 6 6 18"/>',
  };
  return `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${shapes[name] || shapes.workout}</svg>`;
}
function brand() {return `<span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i></span><span class="brand-word">EVOFIT<span>.</span></span>`;}
function parseDate(value) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(value)) return new Date(value+'T00:00:00Z');
  return new Date(value.replace(' ','T') + (/Z$|[+-]\d\d:\d\d$/.test(value) ? '' : 'Z'));
}
function date(value) {return parseDate(value).toLocaleDateString('pt-BR',{timeZone:APP_TZ});}
function dayKey(value) {
  const parts = new Intl.DateTimeFormat('en-CA',{timeZone:APP_TZ,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(value);
  const get = type => parts.find(part => part.type === type).value;
  return `${get('year')}-${get('month')}-${get('day')}`;
}
function todayStart() {return new Date(dayKey(new Date())+'T00:00:00-03:00');}
function recentWorkouts() {
  const start = todayStart(); start.setUTCDate(start.getUTCDate() - dashboardDays + 1);
  return logs('workout').filter(log => parseDate(log.date) >= start && parseDate(log.date) <= new Date());
}
function toast(message) {
  const node = document.querySelector('#toast');
  node.innerHTML = `${icon('check')}<span></span>`;
  node.querySelector('span').textContent = message;
  node.classList.add('visible'); clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => node.classList.remove('visible'), 4800);
}
async function api(path, data, parameters={}) {
  const url = new URL('api.php', document.baseURI); url.searchParams.set('route',path);
  for (const [key,value] of Object.entries(parameters)) url.searchParams.set(key,value);
  const response = await fetch(url, {method: data === undefined ? 'GET' : 'POST', headers:data === undefined ? {} : {'Content-Type':'application/json'}, body:data === undefined ? undefined : JSON.stringify(data)});
  let result;
  try {result = await response.json();} catch (_) {throw Error('O serviço respondeu de forma inesperada. Tente novamente.');}
  if (!response.ok) {const error=Error(result.error || 'Não foi possível concluir.');error.status=response.status;throw error;}
  return result;
}
async function refresh() {
  const epoch=authEpoch,revision=++refreshRevision;
  try {
    const result=await api('state',undefined,{period:rankingPeriod});
    if(epoch!==authEpoch||revision!==refreshRevision)return null;
    state=result;
    if (!state.students.some(item => item.id == student)) student = state.students[0]?.id;
    render(); return true;
  } catch (error) {
    if(epoch!==authEpoch||revision!==refreshRevision)return null;
    if (error.status === 401) {authEpoch++;state=null;resetWorkouts();auth();}
    else if (state) toast(error.message);
    else app.innerHTML = `<section class="service-error"><div class="brand">${brand()}</div><span class="error-symbol">${icon('refresh')}</span><h1>Uma pausa rápida.</h1><p>Não conseguimos conectar ao EvoFit. Confira se o MySQL e o servidor estão ligados.</p><button data-action="retry">Tentar novamente ${icon('arrow-right')}</button></section>`;
    return false;
  }
}
function auth() {
  app.innerHTML = `<div class="auth"><section class="auth-story"><img class="auth-photo" src="images/hero-focus.png" alt="" fetchpriority="high"><div class="auth-shade"></div><div class="brand auth-brand">${brand()}</div><div class="auth-manifesto"><span class="eyebrow">FEITO PARA QUEM SE MOVE.</span><h1>SEU FOCO.<br>SEU TIME.<br><em>SUA EVOLUÇÃO.</em></h1><p>Do primeiro treino à sua próxima conquista.<br>O movimento é seu. O acompanhamento também.</p><div class="auth-stamp">TREINE EM EQUIPE. <span>VÁ MAIS LONGE.</span></div></div><div class="auth-ticker" aria-hidden="true"><span>FORÇA &nbsp; / &nbsp; CONSISTÊNCIA &nbsp; / &nbsp; FOCO &nbsp; / &nbsp; FORÇA &nbsp; / &nbsp; CONSISTÊNCIA &nbsp; / &nbsp; FOCO &nbsp; / &nbsp;</span></div></section><section class="authbox"><div class="auth-mobile-brand brand">${brand()}</div><div class="auth-form-wrap"><span class="section-code">01 / ENTRE NO SEU RITMO</span><h2>${register?'SEU PRÓXIMO<br>PASSO É AQUI.':'DE VOLTA<br>AO SEU FOCO.'}</h2><p class="muted">${register?'Crie sua conta e comece a escrever sua evolução.':'Seu próximo treino está esperando por você.'}</p><form id="auth">${register?field('name','Seu nome','','text','required maxlength="100" autocomplete="name"'):''}${field('email','E-mail','','email','required maxlength="200" autocomplete="email" placeholder="voce@email.com"')}${field('password','Senha','','password',`required minlength="8" maxlength="128" autocomplete="${register?'new-password':'current-password'}" placeholder="Sua senha"`)}<label>Tipo de acesso<select name="role"><option value="aluno">Aluno / atleta</option><option value="personal">Personal trainer</option></select></label><p id="error" class="error" role="alert"></p><button class="auth-submit">${register?'Criar minha conta':'Entrar no EvoFit'} ${icon('arrow-up-right')}</button><button type="button" class="auth-toggle" data-action="toggle">${register?'Já tenho conta. Entrar':'Primeiro acesso? Criar conta'} ${icon('arrow-right')}</button></form><details class="demo"><summary>Quer conhecer antes? Explore a demonstração ${icon('plus')}</summary><div><p><strong>Personal</strong> personal@evofit.demo<br><strong>Aluno</strong> aluno@evofit.demo<br><strong>Senha</strong> EvoFit123!</p><span>Escolha o tipo de acesso correspondente.</span></div></details></div><p class="auth-bottom">SEM ATALHOS. COM ACOMPANHAMENTO. <span>© EVOFIT</span></p></section></div>`;
}
const navItems = () => [['Painel','home','Visão geral'],...(personal()?[['Alunos','users','Atletas']]:[]),['Treinos','workout','Treinos'],['Ranking','trophy','Ranking'],['Histórico','history','Histórico']];
function render() {
  const user = state.user;
  const current = state.students.find(item => item.id == student);
  const titles = {Painel:`BORA, ${user.name.split(' ')[0]}.`,Alunos:'SEU TIME EM MOVIMENTO.',Treinos:'ESCOLHA SEU FOCO.',Ranking:'O FOCO É COLETIVO.',Histórico:'CADA TREINO CONTA.'};
  const subtitles = {Painel:'Consistência que dá para ver. Evolução que é sua.',Alunos:'Acompanhe pessoas. Construa resultados.',Treinos:'Uma divisão. Um objetivo. O seu próximo passo.',Ranking:'Quem treina junto, vai mais longe.',Histórico:'O registro real da sua disciplina.'};
  if (!titles[tab]) tab='Painel';
  app.innerHTML = `<div class="shell"><aside class="sidebar"><button class="brand brand-button" data-tab="Painel" aria-label="EvoFit · início">${brand()}</button><span class="sidebar-kicker">CLUBE DE TREINO</span><nav aria-label="Navegação principal">${navItems().map(([key,symbol,label])=>`<button data-tab="${key}" class="nav-item ${tab===key?'active':''}" ${tab===key?'aria-current="page"':''} aria-label="${key}">${icon(symbol)}<span>${label}</span>${tab===key?'<i class="nav-active-dot"></i>':''}</button>`).join('')}</nav><div class="sidebar-bottom"><div class="club-emblem" aria-hidden="true">EV<span>FOCO / ATIVO</span></div><button class="nav-item logout" data-action="logout">${icon('logout')}<span>Sair da conta</span></button></div></aside><main><header class="top"><div class="top-wordmark"><span class="top-live-dot"></span>SEU CLUBE. SEU RITMO.</div><div class="top-right"><span class="top-date">${new Date().toLocaleDateString('pt-BR',{day:'2-digit',month:'long',timeZone:APP_TZ})}</span><div class="user-chip"><span class="avatar">${esc(initials(user.name))}</span><div><strong>${esc(user.name)}</strong><small>${personal()?'Personal trainer':'Atleta'}</small></div></div><button class="icon-button mobile-logout" data-action="logout" aria-label="Sair da conta">${icon('logout')}</button></div></header><div class="page-heading"><div><span class="section-code">EVOFIT / ${tab==='Painel'?'SEU DIA EM FOCO':tab.toUpperCase()}</span><h1>${esc(titles[tab])}</h1><p class="muted">${subtitles[tab]}</p></div>${personal() && tab!=='Ranking' && tab!=='Alunos'?`<label class="athlete-select">ATLETA<select id="student"><option value="">Selecione um atleta</option>${state.students.map(item=>`<option value="${item.id}" ${item.id==student?'selected':''}>${esc(item.name)}</option>`).join('')}</select></label>`:tab==='Painel'?`<div class="period-control" role="group" aria-label="Período das estatísticas"><button data-days="7" aria-label="Últimos 7 dias" aria-pressed="${dashboardDays===7}" class="${dashboardDays===7?'active':''}">7 dias</button><button data-days="30" aria-label="Últimos 30 dias" aria-pressed="${dashboardDays===30}" class="${dashboardDays===30?'active':''}">30 dias</button></div>`:''}</div>${personal() && tab==='Painel'?`<div class="trainer-context"><span>${icon('users')} Visualizando ${esc(current?.name || 'nenhum atleta')}</span><div class="period-control" role="group" aria-label="Período das estatísticas"><button data-days="7" aria-label="Últimos 7 dias" aria-pressed="${dashboardDays===7}" class="${dashboardDays===7?'active':''}">7 dias</button><button data-days="30" aria-label="Últimos 30 dias" aria-pressed="${dashboardDays===30}" class="${dashboardDays===30?'active':''}">30 dias</button></div></div>`:''}<section id="content" class="view" aria-label="${esc(tab)}">${content()}</section><footer class="page-footer"><span>PROGRESSO SE CONSTRÓI. REP POR REP.</span><span>EVOFIT / CLUBE DE TREINO</span></footer></main></div>`;
  animateCounters();
}
function empty(text) {return `<div class="empty">${icon('target')}<p>${text}</p></div>`;}
function content() {
  if (tab==='Ranking') return rankingPage();
  if (tab==='Alunos') return athletesPage();
  if (!student) return `<section class="card">${empty(personal()?'Seu time está começando. Cadastre o primeiro atleta para criar seus treinos.':'Sua conta ainda não está vinculada a um personal. Seus treinos e o ranking da equipe aparecerão aqui quando houver acompanhamento.')}${personal()?'<button data-tab="Alunos">Adicionar atleta '+icon('plus')+'</button>':''}</section>`;
  if (tab==='Treinos') return workoutSection();
  if (tab==='Histórico') return historyPage();
  return dashboard();
}
function statCard(key,label,value,unit,symbol,accent=false) {return `<article class="stat ${accent?'stat-lime':''}" data-stat="${key}"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon(symbol)}</span></div><strong><span data-count="${value}">${value}</span><small>${unit}</small></strong><span class="stat-note">nos últimos ${dashboardDays} dias</span></article>`;}
function dashboard() {
  const list = recentWorkouts();
  const activeDays = new Set(list.map(log => dayKey(parseDate(log.date)))).size;
  const exercises = list.flatMap(log => log.data.exercises || []).filter(item => item.done === true);
  const maxLoad = exercises.length ? Math.max(...exercises.map(item => Number(item.load)||0)) : 0;
  const workouts = plans('workout');
  const ongoing = workouts.find(plan => progressFor(plan)) || workouts[0];
  const completed = ongoing ? progressFor(ongoing)?.exercises.filter(item=>item.done).length || 0 : 0;
  const total = ongoing?.items.length || 0;
  const percent = total ? Math.round(completed/total*100) : 0;
  const history = logs('workout').slice(-3).reverse();
  return `<div class="dashboard-layout"><div class="dashboard-main"><section class="focus-hero"><img src="images/hero-focus.png" alt="Atleta com halteres em uma academia" fetchpriority="high"><div class="focus-hero-copy"><span class="hero-chip">${icon('bolt')} MOVIMENTO É EVOLUÇÃO</span><h2>CADA REP<br><em>CONTA.</em></h2><p>${personal()?'Transforme planejamento em evolução real.':'Seu treino. Seu ritmo. Sua próxima conquista.'}</p><button class="lime-button" data-tab="Treinos">${personal()?'PLANEJAR TREINOS':'BORA TREINAR'} ${icon('arrow-up-right')}</button></div><span class="hero-edition" aria-hidden="true">O FOCO É SEU.<br>O MOVIMENTO TAMBÉM.</span></section><div class="stats">${statCard('completed','Treinos concluídos',list.length,'treinos','check',true)}${statCard('days','Dias em movimento',activeDays,'dias','calendar')}${statCard('exercises','Exercícios feitos',exercises.length,'exercícios','workout')}${statCard('load','Maior carga registrada',maxLoad,'kg','bolt')}</div><div class="dashboard-charts"><section class="card activity-card"><div class="section-heading"><div><span class="eyebrow">CONSISTÊNCIA EM MOVIMENTO</span><h2>Seu ritmo de treino</h2></div><span class="chart-legend"><i></i> Treinos concluídos</span></div>${activityChart(list)}<div class="chart-bottom"><span>Últimos ${dashboardDays} dias</span><strong>${list.length} ${list.length===1?'treino registrado':'treinos registrados'}</strong></div></section><section class="card current-workout"><div class="section-heading"><div><span class="eyebrow">UM PASSO DE CADA VEZ</span><h2>Seu próximo treino</h2></div>${icon('arrow-up-right')}</div><div class="progress-ring" style="--progress:${percent*3.6}deg" role="img" aria-label="${completed} de ${total} exercícios concluídos"><div><strong>${percent}<small>%</small></strong><span>do treino</span></div></div><h3>${esc(ongoing?.title || 'Seu treino vem aí')}</h3><p class="muted">${ongoing?`${completed} de ${total} exercícios concluídos`:'Seu personal ainda não atribuiu treinos.'}</p>${ongoing?`<button class="secondary" data-open-workout="${ongoing.id}">${completed?'Retomar treino':'Ver exercícios'} ${icon('arrow-right')}</button>`:''}</section></div><section class="card recent-card"><div class="section-heading"><div><span class="eyebrow">CADA CONQUISTA REGISTRADA</span><h2>Últimos movimentos</h2></div><button class="text-button" data-tab="Histórico">Ver histórico ${icon('arrow-right')}</button></div>${history.length?history.map(log=>`<div class="recent-row"><span class="recent-icon">${icon('check')}</span><div><strong>${esc(log.data.title)}</strong><span>${(log.data.exercises||[]).length} exercícios registrados</span></div><time>${date(log.date)}</time><span class="status-pill">Concluído</span></div>`).join(''):empty('O primeiro treino concluído vai aparecer aqui. Bora começar?')}</section></div><aside class="dashboard-rail">${rankingSummary()}<section class="card attendance-card"><div class="section-heading"><div><span class="eyebrow">PRESENÇA QUE CONTA</span><h2>Seu calendário</h2></div>${icon('calendar')}</div>${calendar()}<div class="calendar-key"><i></i> Dia com treino concluído</div></section><div class="club-note"><span class="club-note-icon">${icon('target')}</span><p>COMPITA COM O TIME.<br><strong>EVOLUA COM VOCÊ.</strong></p><span>Cada treino finalizado soma no ranking da sua equipe.</span></div></aside></div>`;
}
function activityChart(list) {
  const start = todayStart();start.setUTCDate(start.getUTCDate()-dashboardDays+1);
  const bins=Array.from({length:dashboardDays},(_,index)=>{const day=new Date(start);day.setUTCDate(day.getUTCDate()+index);return {day,key:dayKey(day),count:0};});
  list.forEach(log=>{const bin=bins.find(item=>item.key===dayKey(parseDate(log.date)));if(bin)bin.count++;});
  const max=Math.max(1,...bins.map(item=>item.count));
  const pts=bins.map((item,index)=>[38+index*524/Math.max(1,bins.length-1),155-item.count/max*110]);
  const labels=bins.filter((_,index)=>dashboardDays===7 || index%5===0 || index===bins.length-1);
  return `<div class="activity-plot"><svg viewBox="0 0 600 200" role="img" aria-label="Treinos concluídos nos últimos ${dashboardDays} dias: ${bins.map(item=>`${item.key}: ${item.count}`).join('; ')}"><title>Frequência de treinos registrados</title>${[0,1,2].map(i=>`<path d="M38 ${45+i*55}H565" stroke="#e4e5df" stroke-dasharray="3 5"/><text x="12" y="${49+i*55}" class="chart-axis">${Math.round(max*(1-i/2))}</text>`).join('')}<path d="M${pts[0][0]},165 ${pts.map(point=>`L${point[0]},${point[1]}`).join(' ')} L${pts.at(-1)[0]},165 Z" fill="#BAF51A" opacity=".2"/><polyline points="${pts.map(point=>point.join(',')).join(' ')}" fill="none" stroke="#181b11" stroke-width="2.5" stroke-linejoin="round"/>${pts.filter((_,index)=>bins[index].count>0).map(point=>`<circle cx="${point[0]}" cy="${point[1]}" r="5" fill="#BAF51A" stroke="#181b11" stroke-width="2"/>`).join('')}${labels.map(item=>{const index=bins.indexOf(item);return `<text x="${pts[index][0]}" y="190" text-anchor="middle" class="chart-axis">${item.day.toLocaleDateString('pt-BR',{day:'2-digit',month:'2-digit',timeZone:APP_TZ})}</text>`;}).join('')}</svg></div>`;
}
function calendar() {
  const now=todayStart(), year=now.getUTCFullYear(), month=now.getUTCMonth();
  const first=new Date(Date.UTC(year,month,1,15)),length=new Date(Date.UTC(year,month+1,0)).getUTCDate();
  const offset=(first.getUTCDay()+6)%7;
  const recorded=new Set(logs('workout').map(log=>dayKey(parseDate(log.date))));
  return `<div class="calendar-title">${now.toLocaleDateString('pt-BR',{month:'long',year:'numeric',timeZone:APP_TZ})}</div><div class="calendar-grid">${['S','T','Q','Q','S','S','D'].map(label=>`<span class="calendar-weekday">${label}</span>`).join('')}${'<span></span>'.repeat(offset)}${Array.from({length},(_,i)=>{const key=`${year}-${String(month+1).padStart(2,'0')}-${String(i+1).padStart(2,'0')}`;return `<span class="calendar-day ${recorded.has(key)?'has-training':''} ${key===dayKey(now)?'today':''}" aria-label="${i+1}${recorded.has(key)?', treino concluído':''}">${i+1}</span>`;}).join('')}</div>`;
}
function rankingControls() {return `<div class="period-control ranking-period" role="group" aria-label="Período do ranking"><button data-ranking-period="month" aria-label="Ranking deste mês" aria-pressed="${rankingPeriod==='month'}" class="${rankingPeriod==='month'?'active':''}">Este mês</button><button data-ranking-period="all" aria-label="Ranking geral" aria-pressed="${rankingPeriod==='all'}" class="${rankingPeriod==='all'?'active':''}">Geral</button></div>`;}
function rankingSummary() {
  const team=state.teamRanking;
  return `<section class="team-card"><div class="team-card-label">${icon('trophy')} O SEU TIME EM FOCO</div><h2>${esc(team?.trainer?team.title:'SEU PRÓXIMO TIME COMEÇA AQUI.')}</h2><p>${team?.trainer?'A mesma equipe. O mesmo propósito.':'Você ainda não está vinculado a um personal.'}</p>${team?.trainer?`<div class="mini-ranking">${team.members.slice(0,4).map(member=>`<div class="mini-ranking-row ${member.isCurrent?'is-me':''}" data-ranking-student="${member.student}"><span class="mini-place">${member.completed?String(member.position).padStart(2,'0'):'—'}</span><span class="rank-avatar">${esc(initials(member.name))}</span><strong>${esc(member.name)}${member.isCurrent?'<small>VOCÊ</small>':''}</strong><span class="rank-score" data-ranking-count>${member.completed}<small>treinos</small></span></div>`).join('')||'<div class="team-zero">Seu primeiro atleta entra aqui.</div>'}</div><div class="team-card-footer"><span>${rankingPeriod==='month'?'RANKING DO MÊS':'HISTÓRICO GERAL'}</span><button class="circle-button" data-tab="Ranking" aria-label="Ver ranking completo">${icon('arrow-up-right')}</button></div>`:''}</section>`;
}
function rankingPage() {
  const team=state.teamRanking;
  if (!team?.trainer) return `<section class="card ranking-unlinked">${empty('Seu ranking aparece quando você faz parte da equipe de um personal. Aqui a competição acontece só entre atletas do mesmo time.')}${personal()?'<button data-tab="Alunos">Formar meu time '+icon('users')+'</button>':''}</section>`;
  const winners=team.members.filter(member=>member.completed>0).slice(0,3);
  const podiumOrder=[winners[1],winners[0],winners[2]].filter(Boolean);
  return `<section class="ranking-arena"><div class="ranking-arena-top"><div><span class="section-code">MESMO TIME. MESMO FOCO.</span><h2>${esc(team.title)}</h2><p>Só os atletas de ${esc(team.trainer.name)}. Só treinos finalizados.</p></div>${rankingControls()}</div><div class="ranking-arena-body"><div class="podium ${winners.length===1?'podium-single':''}">${podiumOrder.map(member=>`<article class="podium-athlete podium-rank-${Math.min(member.position,3)} ${member.isCurrent?'podium-me':''}" data-ranking-student="${member.student}"><div class="podium-person"><span class="podium-avatar">${esc(initials(member.name))}${member.position===1?`<i>${icon('trophy')}</i>`:''}</span><strong>${esc(member.name)}</strong><small>${member.completed} ${member.completed===1?'treino concluído':'treinos concluídos'}${member.isCurrent?' · você':''}</small></div><div class="podium-step"><span>${String(member.position).padStart(2,'0')}</span>${icon(member.position===1?'trophy':'bolt')}</div></article>`).join('')||`<div class="ranking-first">${icon('trophy')}<h3>O PÓDIO ESTÁ ABERTO.</h3><p>Conclua o primeiro treino para colocar seu nome aqui.</p></div>`}</div><div class="ranking-explainer"><span>${icon('check')} 1 treino finalizado = 1 conclusão</span><span>Empates compartilham a mesma posição.</span></div></div></section><section class="card ranking-table-card"><div class="section-heading"><div><span class="eyebrow">TODO MUNDO CONTA</span><h2>Classificação da equipe</h2></div><span class="status-pill">${team.members.length} ${team.members.length===1?'atleta':'atletas'} · ${team.totalCompleted} conclusões</span></div><div class="ranking-table"><div class="ranking-table-header"><span>POSIÇÃO</span><span>ATLETA</span><span>TREINOS</span></div>${team.members.map(member=>`<div class="ranking-table-row ${member.isCurrent?'is-me':''}" data-ranking-student="${member.student}"><span class="ranking-position">${member.completed?String(member.position).padStart(2,'0'):'—'}</span><div class="ranking-person"><span class="rank-avatar">${esc(initials(member.name))}</span><strong>${esc(member.name)}</strong>${member.isCurrent?'<span class="you-pill">VOCÊ</span>':''}</div><strong class="ranking-total" data-ranking-count>${member.completed}<small> concluídos</small></strong></div>`).join('')||empty('Cadastre os primeiros atletas para formar sua equipe.')}</div><p class="hint">${rankingPeriod==='month'?'Contagem do mês atual, no horário de São Paulo.':'Contagem de todos os treinos finalizados no histórico.'} Seus exercícios parciais só entram quando o treino inteiro é concluído.</p></section>`;
}
function athletesPage() {
  return `<div class="athletes-layout"><section class="card"><div class="section-heading"><div><span class="eyebrow">PESSOAS ANTES DOS NÚMEROS</span><h2>Atletas do seu time</h2></div><span class="status-pill">${state.students.length} atletas</span></div>${state.students.map(item=>{const done=state.logs.filter(log=>log.student===item.id&&log.kind==='workout').length;return `<article class="athlete-row"><span class="avatar">${esc(initials(item.name))}</span><div><strong>${esc(item.name)}</strong><p>${esc(item.goal || 'Em busca da próxima conquista.')}</p><small>${esc(item.email)}</small></div><span class="athlete-count"><strong>${done}</strong> treinos</span><button class="icon-button" data-student="${item.id}" aria-label="Ver treinos de ${esc(item.name)}">${icon('arrow-up-right')}</button></article>`;}).join('')||empty('Seu time começa com a primeira pessoa. Adicione um atleta ao lado.')}</section><form id="addstudent" class="card"><span class="eyebrow">UM NOVO COMEÇO</span><h2>Adicionar atleta</h2>${field('name','Nome completo','','text','required maxlength="150"')}${field('email','E-mail de acesso','','email','required maxlength="200"')}${field('password','Senha inicial','','password','required minlength="8" maxlength="128"')}${field('goal','Objetivo no treino','','text','maxlength="500"')}<p class="hint">Compartilhe os dados de acesso diretamente com o atleta. Ele passa a fazer parte somente da sua equipe.</p><button>Cadastrar atleta ${icon('plus')}</button></form></div>`;
}
function historyPage() {
  const list=logs('workout').slice().reverse();
  return `<div class="history-summary"><span>${icon('history')}</span><div><strong>${list.length}</strong><p>treinos que já fazem parte da sua história</p></div></div><section class="history-list">${list.map((log,index)=>`<details class="history-entry" ${index===0?'open':''}><summary><span class="history-check">${icon('check')}</span><span><strong>${esc(log.data.title)}</strong><small>${date(log.date)} · ${(log.data.exercises||[]).length} exercícios</small></span><span class="status-pill">Concluído</span>${icon('arrow-right','history-arrow')}</summary><div class="history-body">${(log.data.exercises||[]).map(exercise=>`<div><span>${esc(exercise.name)}</span><strong>${esc(exercise.load)} <small>kg</small></strong>${icon('check')}</div>`).join('')}${log.data.notes?`<p class="history-notes">${esc(log.data.notes)}</p>`:''}</div></details>`).join('')||`<section class="card">${empty('Seu histórico começa no primeiro treino finalizado. Encontre sua divisão e bora treinar.')}<button data-tab="Treinos">Escolher treino ${icon('arrow-right')}</button></section>`}</section>${loadHistory()}`;
}
function loadHistory() {
  const groups=new Map();
  for (const log of logs('workout')) for (const exercise of log.data.exercises||[]) {if(!groups.has(exercise.name))groups.set(exercise.name,[]);groups.get(exercise.name).push({...exercise,date:log.date});}
  if (!groups.size) return '';
  return `<section class="card load-history"><div class="section-heading"><div><span class="eyebrow">EVOLUÇÃO REP POR REP</span><h2>Suas cargas no tempo</h2></div>${icon('bolt')}</div><div class="load-history-grid">${[...groups.entries()].map(([name,entries])=>{const max=Math.max(1,...entries.map(item=>+item.load));return `<article><div class="row"><h3>${esc(name)}</h3><span>${esc(entries.at(-1).load)} kg</span></div><div class="load-bars" role="img" aria-label="${esc(entries.map(item=>`${date(item.date)}: ${item.load} kg`).join('; '))}">${entries.slice(-12).map(item=>`<div style="--bar-height:${Math.max(3,item.load/max*100)}%"><span>${esc(item.load)}</span><i></i><small>${date(item.date).slice(0,5)}</small></div>`).join('')}</div></article>`;}).join('')}</div></section>`;
}
function editor(plan) {
  return `<form id="plan" class="card plan-editor"><div class="section-heading"><div><span class="eyebrow">PRESCRIÇÃO DO TREINO</span><h2>${plan.id?'Ajuste o próximo passo.':'Um treino. Um objetivo.'}</h2></div>${icon('workout')}</div>${field('title','Título / dia / divisão',plan.title,'text','required maxlength="200" placeholder="Ex.: Treino A · Quadríceps"')}<div id="items">${plan.items.map((item,index)=>editItem('workout',item,index)).join('')}</div><div class="actions"><button type="button" class="secondary" data-action="additem">${icon('plus')} Exercício</button><button>Salvar e atribuir ${icon('check')}</button><button type="button" class="outline" data-action="cancel">Cancelar</button></div></form>`;
}
function editItem(kind,item={},index=0) {
  return `<div class="editor"><div class="row"><h3><span>${String(index+1).padStart(2,'0')}</span> EXERCÍCIO</h3><button type="button" class="text-button remove-item" data-remove="1">Remover ${icon('close')}</button></div>${field('name','Nome',item.name,'text','required maxlength="200"')}<label>Imagem do exercício<select name="illustration">${exerciseIllustrations.map(([key,label])=>`<option value="${key}" ${(item.illustration||'auto')===key?'selected':''}>${label}</option>`).join('')}</select></label><div class="formgrid">${[['sets','Séries',3,'number','min="1" max="1000" required'],['reps','Repetições','12','text','required maxlength="100"'],['load','Carga (kg)',0,'number','min="0" max="1999.5" step="0.5" required'],['rest','Descanso (s)',60,'number','min="0" max="86400" required']].map(([key,label,value,type,extra])=>field(key,label,item[key]??value,type,extra)).join('')}</div>${field('notes','Instruções / observações',item.notes||'','text','maxlength="5000" placeholder="Orientações de execução e ajustes para este atleta"')}</div>`;
}
function animateCounters() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  document.querySelectorAll('.stat [data-count]').forEach(node=>{const value=Number(node.dataset.count),start=performance.now();const tick=now=>{if(!node.isConnected)return;const ratio=Math.min(1,(now-start)/550);const current=value*(1-Math.pow(1-ratio,3));node.textContent=String(Number.isInteger(value)?Math.round(current):Math.round(current*10)/10);if(ratio<1)requestAnimationFrame(tick);};requestAnimationFrame(tick);});
}
function celebrateWorkout() {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const node=document.createElement('div');node.className='celebration';node.setAttribute('aria-hidden','true');
  node.innerHTML=Array.from({length:18},(_,i)=>`<i style="--x:${(i%9-4)*34}px;--y:${-100-(i%5)*35}px;--spin:${i*43}deg;--delay:${i%3*35}ms"></i>`).join('');document.body.appendChild(node);setTimeout(()=>node.remove(),1500);
}
app.addEventListener('click',async event=>{
  const button=event.target.closest('button');if(!button || button.disabled)return;
  try {
    if (button.dataset.action==='retry') {await refresh();return;}
    if (button.dataset.action==='toggle') {if(authRequestPending)return;register=!register;auth();return;}
    if (await handleWorkoutClick(event,button)) return;
    if (button.dataset.tab) {tab=button.dataset.tab;editing=null;render();return;}
    if (button.dataset.days) {dashboardDays=+button.dataset.days;render();return;}
    if (button.dataset.rankingPeriod) {if(rankingPeriod===button.dataset.rankingPeriod)return;const context=captureAuth(),previous=rankingPeriod;rankingPeriod=button.dataset.rankingPeriod;button.disabled=true;if(await refresh()===false&&isAuthCurrent(context)){rankingPeriod=previous;button.disabled=false;}return;}
    if (button.dataset.student) {student=+button.dataset.student;selectedWorkout=null;editing=null;tab='Treinos';render();return;}
    if (button.dataset.new) {selectedWorkout=null;editing={kind:'workout',title:'',items:[{}]};render();return;}
    if (button.dataset.edit) {editing=structuredClone(state.plans.find(plan=>plan.id==button.dataset.edit));render();return;}
    if (button.hasAttribute('data-remove')) {button.closest('.editor').remove();return;}
    if (button.dataset.action==='cancel') {editing=null;render();return;}
    if (button.dataset.action==='additem') {document.querySelector('#items').insertAdjacentHTML('beforeend',editItem('workout',{},document.querySelectorAll('.editor').length));return;}
    if (button.dataset.action==='logout') {
      const epoch=++authEpoch;button.disabled=true;
      try {await api('logout',{});} finally {
        if(epoch===authEpoch){resetWorkouts();state=null;student=undefined;tab='Painel';rankingPeriod='month';auth();}
      }
    }
  } catch (error) {toast(error.message);}
});
app.addEventListener('change',event=>{if(event.target.id==='student'){student=+event.target.value;selectedWorkout=null;editing=null;render();}});
app.addEventListener('submit',async event=>{
  event.preventDefault();const form=event.target,button=form.querySelector('button:not([type="button"])');
  if (!button || button.disabled || (form.id==='auth'&&authRequestPending))return;
  const context=captureAuth();
  if(form.id==='auth')authRequestPending=true;
  const data=Object.fromEntries(new FormData(form));button.disabled=true;const old=button.innerHTML;button.textContent='Salvando…';
  try {
    if (form.id==='auth') {await api(register?'register':'login',data);if(context.epoch!==authEpoch)return;authEpoch++;resetWorkouts();student=undefined;rankingPeriod='month';tab='Painel';await refresh();return;}
    if (form.id==='addstudent') {await api('student',data);if(!isAuthCurrent(context))return;}
    if (form.id==='plan') {const items=[...form.querySelectorAll('.editor')].map(element=>Object.fromEntries([...element.querySelectorAll('input,select')].map(input=>[input.name,input.value])));await api('plan',{...editing,title:data.title,items,student});if(!isAuthCurrent(context))return;editing=null;}
    toast('Salvo. Seu próximo passo já está pronto.');await refresh();
  } catch (error) {if(form.id==='auth'){if(context.epoch===authEpoch&&document.querySelector('#error'))document.querySelector('#error').textContent=error.message;}else if(isAuthCurrent(context))toast(error.message);}
  finally {if(form.id==='auth')authRequestPending=false;button.disabled=false;button.innerHTML=old;}
});
app.addEventListener('input',event=>{
  if(event.target.hasAttribute('data-exercise-load')) {const plan=state.plans.find(plan=>plan.id===+event.target.dataset.plan);if(plan)exerciseDrafts[exerciseKey(plan,+event.target.dataset.index)]=event.target.value;}
  if(event.target.hasAttribute('data-notes-plan'))workoutNotes[event.target.dataset.notesPlan]=event.target.value;
});
app.addEventListener('toggle',event=>{if(event.target.matches('details[data-exercise-key]')&&event.target.isConnected){if(event.target.open)expandedExercises.add(event.target.dataset.exerciseKey);else expandedExercises.delete(event.target.dataset.exerciseKey);}},true);
app.innerHTML='<div class="boot"><span class="brand">'+brand()+'</span><span class="loader"></span><p>Preparando seu próximo movimento.</p></div>';
refresh();
