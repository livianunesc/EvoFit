/* Versão de apresentação: Fetch envia JSON; Flask aplica as regras e o DAO grava no MySQL.
   Nenhum treino ou histórico é simulado no navegador. */
'use strict';

const porId = (id) => document.getElementById(id);
let usuario = null;
let treinos = [];
let enviando = false;
let chaveConclusao = '';
const concluidosNestaVisita = new Set();

function mensagem(texto, tipo = '') {
  porId('mensagem').textContent = texto;
  porId('mensagem').dataset.tipo = tipo;
}

// O mesmo domínio dispensa CORS; a sessão usa cookie HttpOnly administrado pelo servidor.
async function api(caminho, metodo = 'GET', dados) {
  const opcoes = {method: metodo, credentials: 'same-origin', headers: {Accept: 'application/json'}};
  if (dados !== undefined) {
    opcoes.headers['Content-Type'] = 'application/json';
    opcoes.body = JSON.stringify(dados);
  }
  const resposta = await fetch(`/api/${caminho}`, opcoes);
  const conteudo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    if (resposta.status === 401) mostrarAcesso();
    const erro = new Error(conteudo.erro || conteudo.error || 'Não foi possível concluir. Tente novamente.');
    erro.status = resposta.status;
    throw erro;
  }
  return conteudo;
}

// textContent evita executar HTML que tenha vindo de nomes ou de outros dados cadastrados.
function elemento(tag, texto, classe) {
  const novo = document.createElement(tag);
  if (texto !== undefined) novo.textContent = texto;
  if (classe) novo.className = classe;
  return novo;
}

function mostrarAcesso() {
  usuario = null;
  treinos = [];
  porId('painel').hidden = true;
  porId('acesso').hidden = false;
  porId('exercicios').replaceChildren();
  porId('historico').replaceChildren();
  porId('ranking').replaceChildren();
}

async function carregarPainel() {
  const sessao = await api('sessao');
  usuario = sessao.usuario;
  const [lista, historico, ranking] = await Promise.all([api('treinos'), api('historico'), api('ranking')]);
  treinos = lista.treinos;
  porId('usuario').textContent = `${usuario.nome} · ${usuario.papel === 'personal' ? 'Personal' : 'Aluno'}`;
  porId('acesso').hidden = true;
  porId('painel').hidden = false;
  const selecionado = porId('treino').value;
  porId('treino').replaceChildren(elemento('option', 'Selecione um treino'));
  porId('treino').firstChild.value = '';
  for (const treino of treinos) {
    const opcao = elemento('option', usuario.papel === 'personal' ? `${treino.titulo} — ${treino.aluno_nome}` : treino.titulo);
    opcao.value = treino.id;
    porId('treino').append(opcao);
  }
  porId('sem-treinos').hidden = treinos.length > 0;
  if (treinos.some((treino) => String(treino.id) === selecionado)) porId('treino').value = selecionado;
  else if (treinos.length) porId('treino').value = treinos[0].id;
  desenharTreino();
  desenharHistorico(historico.registros);
  desenharRanking(ranking.ranking);
}

function desenharTreino() {
  const treino = treinos.find((item) => String(item.id) === porId('treino').value);
  porId('exercicios').replaceChildren();
  porId('form-treino').hidden = !treino;
  if (!treino) return;
  chaveConclusao = crypto.randomUUID();
  const aluno = usuario.papel === 'aluno';
  porId('orientacao').textContent = aluno
    ? 'Marque os exercícios feitos, confira as cargas e conclua para registrar no histórico.'
    : 'Nesta versão o personal consulta os treinos. Abra a versão completa para cadastrar e editar.';
  treino.exercicios.forEach((exercicio, indice) => {
    const grupo = elemento('fieldset', undefined, 'exercicio');
    grupo.append(elemento('legend', `${indice + 1}. ${exercicio.nome}`));
    grupo.append(elemento('p', `${exercicio.series} séries · ${exercicio.repeticoes} repetições · ${exercicio.descanso}s de descanso`));
    if (exercicio.instrucoes) grupo.append(elemento('p', exercicio.instrucoes));
    const rotuloCarga = elemento('label', 'Carga utilizada (kg)');
    rotuloCarga.htmlFor = `carga-${indice}`;
    const carga = elemento('input');
    Object.assign(carga, {id: `carga-${indice}`, type: 'number', min: '0', max: '1999.99', step: '0.01', required: true, value: exercicio.carga, disabled: !aluno});
    carga.dataset.carga = '';
    carga.addEventListener('input', atualizarBotao);
    grupo.append(rotuloCarga, carga);
    if (aluno) {
      const rotuloFeito = elemento('label', undefined, 'marcacao');
      const feito = elemento('input');
      Object.assign(feito, {type: 'checkbox', required: true});
      feito.dataset.feito = '';
      feito.addEventListener('change', atualizarBotao);
      rotuloFeito.append(feito, elemento('span', 'Exercício concluído'));
      grupo.append(rotuloFeito);
    }
    porId('exercicios').append(grupo);
  });
  porId('concluir').hidden = !aluno;
  atualizarBotao();
}

function atualizarBotao() {
  const feitos = [...document.querySelectorAll('[data-feito]')];
  const cargas = [...document.querySelectorAll('[data-carga]')];
  const concluido = concluidosNestaVisita.has(porId('treino').value);
  porId('concluir').disabled = enviando || concluido || !feitos.length || !feitos.every((item) => item.checked) || !cargas.every((item) => item.checkValidity());
  porId('concluir').textContent = enviando ? 'Registrando…' : concluido ? 'Treino registrado nesta visita' : 'Concluir treino';
}

function dataBrasileira(valor) {
  // DATETIME do MySQL representa UTC; o navegador apresenta no fuso de São Paulo.
  const iso = String(valor).replace(' ', 'T');
  const data = new Date(/[zZ]$|[+-]\d\d:\d\d$/.test(iso) ? iso : `${iso}Z`);
  return Number.isNaN(data.getTime()) ? String(valor) : data.toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo'});
}

function desenharHistorico(registros) {
  const lista = porId('historico');
  lista.replaceChildren();
  if (!registros.length) lista.append(elemento('li', 'Seu primeiro treino concluído aparecerá aqui.'));
  for (const registro of registros.slice(0, 8)) {
    const linha = elemento('li');
    linha.append(elemento('strong', registro.titulo));
    linha.append(elemento('small', `${dataBrasileira(registro.concluido_em)} · soma das cargas: ${Number(registro.carga_total).toLocaleString('pt-BR')} kg`));
    if (usuario.papel === 'personal') linha.append(elemento('small', registro.aluno_nome));
    lista.append(linha);
  }
}

function desenharRanking(classificacao) {
  const lista = porId('ranking');
  lista.replaceChildren();
  if (!classificacao.length) lista.append(elemento('li', 'A equipe ainda não tem participantes no ranking.'));
  for (const pessoa of classificacao) {
    const linha = elemento('li');
    linha.append(elemento('span', `${pessoa.posicao}º · ${pessoa.nome}`), elemento('strong', `${pessoa.total} treinos`));
    lista.append(linha);
  }
}

porId('exemplo').addEventListener('click', () => {
  porId('email').value = 'aluno@evofit.demo';
  porId('senha').value = 'EvoFit123!';
  mensagem('Exemplo preenchido. Clique em Entrar para consultar o banco.');
});

porId('form-login').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  porId('entrar').disabled = true;
  mensagem('Entrando…');
  try {
    await api('login', 'POST', {email: porId('email').value.trim(), senha: porId('senha').value});
    porId('senha').value = '';
    concluidosNestaVisita.clear();
    await carregarPainel();
    mensagem('Bem-vindo! Escolha seu treino.', 'sucesso');
  } catch (erro) { mensagem(erro.message, 'erro'); }
  finally { porId('entrar').disabled = false; }
});

porId('treino').addEventListener('change', desenharTreino);
porId('form-treino').addEventListener('submit', async (evento) => {
  evento.preventDefault();
  if (porId('concluir').disabled) return;
  const id = porId('treino').value;
  const treino = treinos.find((item) => String(item.id) === id);
  enviando = true;
  atualizarBotao();
  porId('treino').disabled = true;
  mensagem('Salvando o treino no banco…');
  let salvo = false;
  try {
    // A chave impede duplicatas; a versão recusa uma ficha alterada durante a execução.
    await api(`treinos/${id}/concluir`, 'POST', {cargas: [...document.querySelectorAll('[data-carga]')].map((item) => Number(item.value)), chave: chaveConclusao, versao: treino.versao});
    salvo = true;
    concluidosNestaVisita.add(id);
    await carregarPainel();
    mensagem('Treino registrado! Histórico e ranking foram atualizados.', 'sucesso');
  } catch (erro) { mensagem(salvo ? `Treino salvo, mas não foi possível atualizar o painel: ${erro.message}` : erro.message, 'erro'); }
  finally { enviando = false; porId('treino').disabled = false; atualizarBotao(); }
});

porId('sair').addEventListener('click', async () => {
  porId('sair').disabled = true;
  try { await api('logout', 'POST', {}); mostrarAcesso(); mensagem('Você saiu da conta.'); }
  catch (erro) { mensagem(erro.message, 'erro'); }
  finally { porId('sair').disabled = false; }
});

// Retoma uma sessão existente após recarregar a página; a ausência de sessão é normal.
(async () => {
  try { await carregarPainel(); }
  catch (erro) { if (erro.status !== 401) mensagem(erro.message || 'Servidor indisponível. Confira se o Flask e o MySQL estão ligados.', 'erro'); }
})();
