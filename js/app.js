import {requisicao} from './api.js';

// O DOM recebe textos, nunca HTML vindo do banco. Isso evita executar conteúdo cadastrado.
const $ = (seletor, contexto = document) => contexto.querySelector(seletor);
const pagina = document.body.dataset.pagina;
let usuario;
function elemento(tag, texto, classe) {
  const item = document.createElement(tag);
  if (texto !== undefined) item.textContent = String(texto ?? '');
  if (classe) item.className = classe;
  return item;
}
function mensagem(texto, tipo = 'sucesso') {
  const status = $('#status');
  status.textContent = texto;
  status.dataset.tipo = tipo;
}
function vazio(destino, texto) {
  destino.replaceChildren(elemento('p', texto, 'vazio'));
}
function botao(texto, acao, classe = 'secundario pequeno') {
  const item = elemento('button', texto, classe);
  item.type = 'button';
  item.addEventListener('click', acao);
  return item;
}
function link(texto, destino, classe = '') {
  const item = elemento('a', texto, classe);
  item.href = destino;
  return item;
}
function tabela(colunas, linhas) {
  const rolagem = elemento('div', undefined, 'tabela-scroll');
  const tabela = elemento('table');
  const cabecalho = elemento('thead');
  const titulos = elemento('tr');
  colunas.forEach(titulo => {
    const th = elemento('th', titulo);
    th.scope = 'col';
    titulos.append(th);
  });
  cabecalho.append(titulos);
  const corpo = elemento('tbody');
  linhas.forEach(celulas => {
    const linha = elemento('tr');
    celulas.forEach(valor => {
      const td = elemento('td');
      if (valor instanceof Node) td.append(valor);
      else td.textContent = String(valor ?? '');
      linha.append(td);
    });
    corpo.append(linha);
  });
  tabela.append(cabecalho, corpo);
  rolagem.append(tabela);
  return rolagem;
}
// Um botão desabilitado impede envio duplo; finally o libera mesmo em caso de erro.
async function executar(botaoAcao, acao) {
  if (botaoAcao.disabled) return;
  botaoAcao.disabled = true;
  const original = botaoAcao.textContent;
  botaoAcao.textContent = 'Aguarde…';
  mensagem('Processando…');
  try { await acao(); }
  catch (erro) { mensagem(erro.message, 'erro'); }
  finally {
    botaoAcao.disabled = false;
    if (botaoAcao.textContent === 'Aguarde…') botaoAcao.textContent = original;
  }
}
function configurarSessao() {
  $('#usuario-nome').textContent = `${usuario.nome} · ${usuario.papel === 'personal' ? 'Personal' : 'Aluno'}`;
  $('#sair').hidden = false;
  document.querySelectorAll('[data-personal]').forEach(item => { item.hidden = usuario.papel !== 'personal'; });
  $('#sair').addEventListener('click', evento => executar(evento.currentTarget, async () => {
    await requisicao('logout', {metodo: 'POST', dados: {}});
    location.href = '/';
  }));
}
function configurarLogin() {
  $('#entrada').hidden = false;
  $('#form-login').addEventListener('submit', evento => {
    evento.preventDefault();
    const form = evento.currentTarget;
    executar($('button[type=submit]', form), async () => {
      await requisicao('login', {metodo: 'POST', dados: {email: form.email.value.trim(), senha: form.senha.value}});
      location.href = '/';
    });
  });
  document.querySelectorAll('[data-demo]').forEach(item => item.addEventListener('click', () => {
    $('#email').value = `${item.dataset.demo}@evofit.demo`;
    $('#senha').value = 'EvoFit123!';
    $('#email').focus();
  }));
}
function renderizarRanking(destino, ranking) {
  if (!ranking.length) return vazio(destino, 'Sua equipe ainda não registrou treinos concluídos. Cada conquista começa com o primeiro treino.');
  destino.replaceChildren();
  ranking.forEach(pessoa => {
    const linha = elemento('div', undefined, 'item-ranking');
    const posicao = elemento('span', `${pessoa.posicao}º`, 'posicao');
    const nome = elemento('strong', pessoa.nome);
    const total = elemento('small', `${pessoa.total} treino${Number(pessoa.total) === 1 ? '' : 's'}`);
    linha.append(posicao, nome, total);
    destino.append(linha);
  });
}
async function painel() {
  $('#painel').hidden = false;
  $('#saudacao').textContent = `Bom treino, ${usuario.nome.split(' ')[0]}!`;
  $('#texto-painel').textContent = usuario.papel === 'personal'
    ? 'Transforme planejamento em evolução real. Organize os treinos e acompanhe cada conquista do seu time.'
    : 'Um exercício de cada vez. Siga seu treino e registre as conquistas da sua jornada.';
  const [treinos, historico, ranking] = await Promise.all([
    requisicao('treinos'), requisicao('historico'), requisicao('ranking')
  ]);
  $('#total-treinos').textContent = treinos.treinos.length;
  $('#total-concluidos').textContent = historico.registros.length;
  if (usuario.papel === 'personal') {
    const dados = await requisicao('alunos');
    $('#total-pessoas').textContent = dados.alunos.length;
  } else {
    $('#total-pessoas').textContent = new Set(historico.registros.map(item => String(item.concluido_em).slice(0, 10))).size;
    $('#rotulo-pessoas').textContent = 'Dias com treino';
  }
  const lista = $('#proximos-treinos');
  if (!treinos.treinos.length) vazio(lista, usuario.papel === 'personal' ? 'Cadastre seus alunos e prescreva o primeiro treino.' : 'Seu personal ainda não prescreveu um treino para você.');
  else {
    treinos.treinos.slice(0, 3).forEach(treino => {
      const linha = elemento('div', undefined, 'exercicio');
      linha.append(elemento('h3', treino.titulo), elemento('p', `${treino.aluno_nome} · ${treino.exercicios.length} exercícios`));
      lista.append(linha);
    });
    lista.append(link('Ir para os treinos →', '/pages/treinos.html', 'botao secundario pequeno'));
  }
  renderizarRanking($('#ranking-resumo'), ranking.ranking.slice(0, 5));
  mensagem('');
}

// CRUD: POST insere, GET consulta, PUT atualiza e DELETE exclui. A API valida novamente.
async function alunos() {
  const form = $('#form-aluno');
  let cadastrados = [];
  function limpar() {
    form.reset();
    form.elements.id.value = '';
    form.senha.required = true;
    $('#senha-opcional').textContent = '';
    $('#titulo-form').textContent = 'Cadastrar aluno';
    $('#salvar-aluno').textContent = 'Cadastrar aluno';
    $('#cancelar-aluno').hidden = true;
  }
  function editar(aluno) {
    form.elements.id.value = aluno.id;
    for (const campo of ['nome', 'email', 'objetivo']) form.elements[campo].value = aluno[campo] || '';
    form.senha.value = '';
    form.senha.required = false;
    $('#senha-opcional').textContent = '(opcional na edição)';
    $('#titulo-form').textContent = 'Editar aluno';
    $('#salvar-aluno').textContent = 'Salvar alterações';
    $('#cancelar-aluno').hidden = false;
    form.nome.focus();
  }
  async function carregar() {
    cadastrados = (await requisicao('alunos')).alunos;
    $('#contagem-alunos').textContent = `${cadastrados.length} alunos`;
    const destino = $('#lista-alunos');
    if (!cadastrados.length) return vazio(destino, 'Nenhum aluno cadastrado. Comece pelo formulário acima.');
    destino.replaceChildren(tabela(['Nome', 'E-mail', 'Objetivo', 'Ações'], cadastrados.map(aluno => {
      const acoes = elemento('div', undefined, 'acoes');
      acoes.append(botao('Editar', () => editar(aluno)), botao('Excluir', evento => {
        if (!confirm(`Excluir o cadastro de ${aluno.nome}?`)) return;
        executar(evento.currentTarget, async () => {
          await requisicao(`alunos/${aluno.id}`, {metodo: 'DELETE'});
          if (Number(form.elements.id.value) === Number(aluno.id)) limpar();
          await carregar();
          mensagem('Aluno excluído.');
        });
      }, 'perigo pequeno'));
      return [aluno.nome, aluno.email, aluno.objetivo || 'Não informado', acoes];
    })));
  }
  $('#cancelar-aluno').addEventListener('click', limpar);
  form.addEventListener('submit', evento => {
    evento.preventDefault();
    executar($('#salvar-aluno'), async () => {
      const id = form.elements.id.value;
      const dados = {nome: form.nome.value.trim(), email: form.email.value.trim(), objetivo: form.objetivo.value.trim()};
      if (form.senha.value) dados.senha = form.senha.value;
      await requisicao(id ? `alunos/${id}` : 'alunos', {metodo: id ? 'PUT' : 'POST', dados});
      limpar();
      await carregar();
      mensagem(id ? 'Cadastro atualizado.' : 'Aluno cadastrado. Agora você pode prescrever seu treino.');
    });
  });
  await carregar();
}
async function exercicios() {
  const form = $('#form-exercicio');
  function limpar() {
    form.reset();
    form.elements.id.value = '';
    $('#titulo-form').textContent = 'Cadastrar exercício';
    $('#salvar-exercicio').textContent = 'Cadastrar exercício';
    $('#cancelar-exercicio').hidden = true;
  }
  async function carregar() {
    const itens = (await requisicao('exercicios')).exercicios;
    const destino = $('#lista-exercicios');
    if (!itens.length) return vazio(destino, 'Nenhum exercício cadastrado. Adicione o primeiro movimento.');
    destino.replaceChildren(tabela(['Exercício', 'Grupo muscular', 'Instruções', 'Ações'], itens.map(item => {
      const acoes = elemento('div', undefined, 'acoes');
      acoes.append(botao('Editar', () => {
        form.elements.id.value = item.id;
        for (const campo of ['nome', 'grupo_muscular', 'instrucoes']) form.elements[campo].value = item[campo] || '';
        $('#titulo-form').textContent = 'Editar exercício';
        $('#salvar-exercicio').textContent = 'Salvar alterações';
        $('#cancelar-exercicio').hidden = false;
        form.nome.focus();
      }), botao('Excluir', evento => {
        if (!confirm(`Excluir ${item.nome} do catálogo?`)) return;
        executar(evento.currentTarget, async () => {
          await requisicao(`exercicios/${item.id}`, {metodo: 'DELETE'});
          if (Number(form.elements.id.value) === Number(item.id)) limpar();
          await carregar();
          mensagem('Exercício excluído.');
        });
      }, 'perigo pequeno'));
      return [item.nome, item.grupo_muscular, item.instrucoes, acoes];
    })));
  }
  $('#cancelar-exercicio').addEventListener('click', limpar);
  form.addEventListener('submit', evento => {
    evento.preventDefault();
    executar($('#salvar-exercicio'), async () => {
      const id = form.elements.id.value;
      const dados = Object.fromEntries(['nome', 'grupo_muscular', 'instrucoes'].map(campo => [campo, form.elements[campo].value.trim()]));
      await requisicao(id ? `exercicios/${id}` : 'exercicios', {metodo: id ? 'PUT' : 'POST', dados});
      limpar();
      await carregar();
      mensagem(id ? 'Exercício atualizado.' : 'Exercício cadastrado no catálogo.');
    });
  });
  await carregar();
}

async function treinos() {
  const form = $('#form-treino');
  const personal = usuario.papel === 'personal';
  let catalogo = [];
  let numeroCampo = 0;
  function campo(rotulo, nome, valor, tipo = 'number', atributos = {}) {
    const div = elemento('div', undefined, 'campo');
    const id = `prescricao-${++numeroCampo}`;
    const label = elemento('label', rotulo);
    label.htmlFor = id;
    const input = elemento('input');
    Object.assign(input, {id, name: nome, type: tipo, value: valor, required: true}, atributos);
    div.append(label, input);
    return div;
  }
  function adicionar(item = {}) {
    const linha = elemento('div', undefined, 'editor-exercicio');
    const id = `movimento-${++numeroCampo}`;
    const label = elemento('label', 'Exercício');
    label.htmlFor = id;
    const select = elemento('select');
    select.id = id;
    select.name = 'exercicio_id';
    select.required = true;
    const inicial = elemento('option', 'Selecione o movimento');
    inicial.value = '';
    select.append(inicial);
    catalogo.forEach(exercicio => {
      const option = elemento('option', `${exercicio.nome} · ${exercicio.grupo_muscular}`);
      option.value = exercicio.id;
      select.append(option);
    });
    select.value = item.exercicio_id || '';
    const campos = elemento('div', undefined, 'campos');
    campos.append(
      campo('Séries', 'series', item.series ?? 3, 'number', {min: 1, max: 20, step: 1}),
      campo('Repetições', 'repeticoes', item.repeticoes ?? '12', 'text', {maxLength: 30}),
      campo('Carga (kg)', 'carga', item.carga ?? 0, 'number', {min: 0, max: 1999, step: 0.01}),
      campo('Descanso (s)', 'descanso', item.descanso ?? 60, 'number', {min: 0, max: 1800, step: 1})
    );
    linha.append(label, select, campos, botao('Remover movimento', () => linha.remove(), 'perigo pequeno'));
    $('#itens-treino').append(linha);
  }
  function limpar() {
    form.reset();
    form.elements.id.value = '';
    $('#itens-treino').replaceChildren();
    adicionar();
    $('#titulo-form').textContent = 'Prescrever treino';
    $('#cancelar-treino').hidden = true;
  }
  function editar(treino) {
    form.elements.id.value = treino.id;
    form.aluno_id.value = treino.aluno_id;
    form.titulo.value = treino.titulo;
    $('#itens-treino').replaceChildren();
    treino.exercicios.forEach(adicionar);
    $('#titulo-form').textContent = 'Editar treino';
    $('#cancelar-treino').hidden = false;
    form.titulo.focus();
  }
  async function carregar() {
    const itens = (await requisicao('treinos')).treinos;
    $('#contagem-treinos').textContent = `${itens.length} treinos`;
    const destino = $('#lista-treinos');
    destino.replaceChildren();
    if (!itens.length) return vazio(destino, personal ? 'Nenhum treino prescrito. Crie um treino no formulário acima.' : 'Você ainda não tem treinos prescritos. Fale com seu personal.');
    itens.forEach(treino => {
      const card = elemento('article', undefined, 'cartao treino');
      card.append(elemento('span', treino.aluno_nome, 'sobretitulo'), elemento('h2', treino.titulo));
      const entradas = [];
      const marcadores = [];
      treino.exercicios.forEach((exercicio, indice) => {
        const bloco = elemento('section', undefined, 'exercicio');
        bloco.append(elemento('h3', `${indice + 1}. ${exercicio.nome}`));
        bloco.append(elemento('p', `${exercicio.series} séries · ${exercicio.repeticoes} repetições · ${exercicio.descanso}s de descanso`));
        bloco.append(elemento('p', exercicio.instrucoes));
        if (personal) bloco.append(elemento('strong', `${Number(exercicio.carga).toLocaleString('pt-BR')} kg prescritos`));
        else {
          const id = `carga-${treino.id}-${indice}`;
          const label = elemento('label', 'Carga utilizada (kg)');
          label.htmlFor = id;
          const carga = elemento('input', undefined, 'carga');
          Object.assign(carga, {id, type: 'number', min: 0, max: 1999, step: 0.01, value: exercicio.carga, required: true});
          const checar = elemento('div', undefined, 'checar');
          const checkbox = elemento('input');
          Object.assign(checkbox, {id: `feito-${treino.id}-${indice}`, type: 'checkbox'});
          const texto = elemento('label', 'Exercício concluído');
          texto.htmlFor = checkbox.id;
          checar.append(checkbox, texto);
          bloco.append(label, carga, checar);
          entradas.push(carga);
          marcadores.push(checkbox);
        }
        card.append(bloco);
      });
      const acoes = elemento('div', undefined, 'acoes');
      acoes.style.marginTop = '20px';
      if (personal) {
        acoes.append(botao('Editar treino', () => editar(treino)), botao('Excluir treino', evento => {
          if (!confirm(`Excluir o treino ${treino.titulo}? Treinos com histórico serão preservados.`)) return;
          executar(evento.currentTarget, async () => {
            await requisicao(`treinos/${treino.id}`, {metodo: 'DELETE'});
            if (Number(form.elements.id.value) === Number(treino.id)) limpar();
            await carregar();
            mensagem('Treino excluído.');
          });
        }, 'perigo pequeno'));
      } else {
        // A chave identifica esta tentativa: uma repetição de rede não duplica o histórico.
        const chave = crypto.randomUUID();
        acoes.append(botao('Concluir treino', evento => {
          if (!marcadores.length || !marcadores.every(item => item.checked)) {
            mensagem('Marque cada exercício concluído antes de registrar o treino.', 'erro');
            card.scrollIntoView({block: 'start'});
            return;
          }
          for (const entrada of entradas) if (!entrada.reportValidity()) return;
          executar(evento.currentTarget, async () => {
            await requisicao(`treinos/${treino.id}/concluir`, {metodo: 'POST', dados: {cargas: entradas.map(item => Number(item.value)), chave, versao: treino.versao}});
            await carregar();
            mensagem('Treino concluído! Sua conquista já está no histórico e no ranking.');
            $('#status').scrollIntoView({block: 'center'});
          });
        }, 'lima'));
        card.append(elemento('p', 'Confira suas cargas e marque os exercícios realizados. Os campos deste treino são limpos ao sair da página.', 'ajuda'));
      }
      card.append(acoes);
      destino.append(card);
    });
  }
  if (personal) {
    $('#editor-treino').hidden = false;
    $('#intro-treinos').textContent = 'Prescreva a rotina dos seus alunos com exercícios, séries, repetições e cargas.';
    const [dadosCatalogo, dadosAlunos] = await Promise.all([requisicao('exercicios'), requisicao('alunos')]);
    catalogo = dadosCatalogo.exercicios;
    dadosAlunos.alunos.forEach(aluno => {
      const option = elemento('option', aluno.nome);
      option.value = aluno.id;
      form.aluno_id.append(option);
    });
    $('#adicionar-exercicio').addEventListener('click', () => adicionar());
    $('#cancelar-treino').addEventListener('click', limpar);
    adicionar();
    form.addEventListener('submit', evento => {
      evento.preventDefault();
      executar($('#salvar-treino'), async () => {
        const linhas = [...$('#itens-treino').children];
        if (!linhas.length) throw new Error('Adicione ao menos um exercício ao treino.');
        const itens = linhas.map(linha => {
          const valor = nome => $(`[name="${nome}"]`, linha).value;
          return {exercicio_id: Number(valor('exercicio_id')), series: Number(valor('series')), repeticoes: valor('repeticoes').trim(), carga: Number(valor('carga')), descanso: Number(valor('descanso'))};
        });
        const dados = {aluno_id: Number(form.aluno_id.value), titulo: form.titulo.value.trim(), exercicios: itens};
        const id = form.elements.id.value;
        await requisicao(id ? `treinos/${id}` : 'treinos', {metodo: id ? 'PUT' : 'POST', dados});
        limpar();
        await carregar();
        mensagem(id ? 'Treino atualizado.' : 'Treino prescrito. O aluno já pode consultá-lo.');
      });
    });
    if (!catalogo.length || !dadosAlunos.alunos.length) mensagem('Antes de prescrever, cadastre ao menos um aluno e um exercício.');
  }
  await carregar();
}
async function relatorios() {
  const [historico, ranking] = await Promise.all([requisicao('historico'), requisicao('ranking')]);
  renderizarRanking($('#ranking-completo'), ranking.ranking);
  const destino = $('#lista-historico');
  if (!historico.registros.length) return vazio(destino, 'Nenhum treino concluído ainda. Suas conquistas aparecerão aqui.');
  destino.replaceChildren(tabela(['Quando', 'Aluno', 'Treino', 'Soma das cargas'], historico.registros.map(registro => {
    // O banco armazena UTC. A exibição usa explicitamente o fuso de São Paulo.
    let data = String(registro.concluido_em);
    if (!/[zZ]|[+-]\d\d:\d\d$/.test(data)) data = data.replace(' ', 'T') + 'Z';
    const formatada = new Date(data).toLocaleString('pt-BR', {timeZone: 'America/Sao_Paulo', dateStyle: 'short', timeStyle: 'short'});
    return [formatada, registro.aluno_nome, registro.titulo, `${Number(registro.carga_total).toLocaleString('pt-BR')} kg`];
  })));
}
async function iniciar() {
  mensagem('Carregando sua conta…');
  try {
    usuario = (await requisicao('sessao')).usuario;
  } catch (erro) {
    if (erro.status === 401) {
      if (pagina !== 'painel') { location.replace('/?entrar=1'); return; }
      configurarLogin();
      mensagem(location.search.includes('entrar') ? 'Entre na sua conta para continuar.' : '');
      return;
    }
    // Se o banco estiver indisponível, o formulário continua visível com a causa informada.
    if (pagina === 'painel') configurarLogin();
    mensagem(erro.message, 'erro');
    return;
  }
  configurarSessao();
  if (['alunos', 'exercicios'].includes(pagina)) {
    if (usuario.papel !== 'personal') {
      mensagem('Esta página é destinada ao personal. Você pode consultar seus treinos e seu histórico.', 'erro');
      return;
    }
    $('#area-restrita').hidden = false;
  }
  mensagem('Carregando dados…');
  try {
    await ({painel, alunos, exercicios, treinos, relatorios}[pagina] || painel)();
    if ($('#status').textContent === 'Carregando dados…') mensagem('');
  } catch (erro) { mensagem(erro.message, 'erro'); }
}
iniciar();
