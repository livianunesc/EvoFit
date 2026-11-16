# EvoFit — apresentação simples

**Autora do projeto:** Livia Nunes Coelho

Esta versão reduzida usa **HTML semântico, CSS separado e JavaScript com Fetch**, consumindo a **mesma API Python/Flask e o mesmo MySQL** da versão completa. Os dados fictícios de demonstração são persistidos no MySQL e consultados pela API, sem armazenamento em `localStorage`.

Inicie o projeto seguindo o README da raiz e abra o caminho `/apresentacao/` no servidor Flask. **Não abra `index.html` por `file://`**: o login e a gravação dependem da API e do banco ligados. A conta de demonstração só existe depois de executar a inicialização com seed do projeto.

## Roteiro de aproximadamente 3 minutos

1. **30 s — separar responsabilidades.** Abra `index.html`, `estilo.css` e `app.js`. Aponte a estrutura HTML, as classes CSS e a função `api()`, que envia JSON com Fetch. No Python, mostre a rota, o DAO e a consulta parametrizada.
2. **30 s — entrar.** Clique em “Preencher conta de exemplo” e em “Entrar”. Isso autentica o aluno `aluno@evofit.demo`, senha pública de desenvolvimento `EvoFit123!`. A sessão é mantida pelo servidor em cookie HttpOnly.
3. **1 min — executar um treino.** Selecione o treino, leia séries/repetições e ajuste as cargas. Marque cada exercício. O botão só fica disponível quando todos estiverem concluídos e os campos forem válidos. Clique uma vez para registrar.
4. **30 s — comprovar persistência.** Veja o histórico e o ranking atualizados. Recarregue a página: o registro permanece porque está no MySQL. A soma das cargas exibida é uma soma simples das cargas utilizadas, não uma medida de volume de treino.
5. **30 s — encerrar.** Mostre “Versão completa” para explicar os cadastros de alunos, exercícios e treinos, depois saia da conta.

## O que foi simplificado

A apresentação concentra login, consulta de treinos, conclusão, histórico e ranking em uma página. Os cadastros e as alterações ficam na versão completa. Uma conta de personal pode consultar os dados da própria equipe, mas só o aluno conclui o próprio treino. O catálogo e a prescrição vêm do banco; se estiverem vazios, o personal deve cadastrá-los na versão completa.

O botão de conclusão não registra novamente o mesmo treino nesta visita. A chave enviada também protege contra repetição da mesma requisição no servidor. Para iniciar outra visita de apresentação, recarregue a página; isso não apaga registros anteriores.

PHP tem sua demonstração complementar no módulo de relatório do projeto principal. O acesso da interface reduzida ao servidor segue o mesmo fluxo Fetch → Flask → DAO → MySQL da aplicação principal.

## Repetir a verificação de navegador

Use um **banco exclusivo de testes**, inicializado com as contas demo. O teste acrescenta uma conclusão de treino; não use o banco de apresentação que deseja manter intacto ou um banco de uso real. Os comandos abaixo são para Bash, executados na raiz do projeto. O endereço deve apontar à instância de testes configurada; `4185` é o exemplo usado na validação.

```sh
python -m pip install playwright
python -m playwright install chromium
EVOFIT_TEST_URL=http://127.0.0.1:4185 EVOFIT_CONFIRMAR_BANCO_TESTE=1 python tests/browser_apresentacao_academica.py
```

No PowerShell, defina as variáveis antes da execução:

```powershell
$env:EVOFIT_TEST_URL = "http://127.0.0.1:4185"
$env:EVOFIT_CONFIRMAR_BANCO_TESTE = "1"
python tests/browser_apresentacao_academica.py
```

O teste não assume um endereço padrão e exige a confirmação de que o banco é de testes. Verifica login de aluno/personal, conclusão parcial bloqueada, histórico/ranking atualizados, persistência ao recarregar, consulta do personal, logout e largura móvel de 375 px. Confere erros JavaScript e respostas HTTP inesperadas; a resposta `401` inicial de sessão anônima é esperada.

As capturas são salvas em uma pasta temporária do sistema, informada ao final. Para escolher outra pasta, defina `EVOFIT_SCREENSHOT_DIR`. Se necessário, `CHROMIUM_PATH` seleciona um executável de Chromium/Chrome existente. Capturas da validação executada estão em [desktop](../docs/imagens/apresentacao-desktop.png) e [mobile](../docs/imagens/apresentacao-mobile.png); os nomes exibidos pertencem às contas fictícias de teste.
