/** Comunicação HTTP centralizada: o Fetch leva JSON ao Flask e recebe JSON do DAO. */
export async function requisicao(caminho, {metodo = 'GET', dados} = {}) {
  const resposta = await fetch(`/api/${caminho}`, {
    method: metodo,
    credentials: 'same-origin',
    headers: dados === undefined ? {'Accept': 'application/json'} : {'Accept': 'application/json', 'Content-Type': 'application/json'},
    body: dados === undefined ? undefined : JSON.stringify(dados)
  });
  const conteudo = await resposta.json().catch(() => ({}));
  if (!resposta.ok) {
    const erro = new Error(conteudo.erro || conteudo.error || 'Não foi possível completar a operação.');
    erro.status = resposta.status;
    throw erro;
  }
  return conteudo;
}
