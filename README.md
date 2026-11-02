# EvoFit

Plataforma de acompanhamento fitness em português, com áreas de personal e aluno, desenvolvida para Livia Nunes Coelho.

## Executar

Requer Python 3.10 ou superior, com SQLite, sem pacotes externos.

```sh
cd /workspace/EvoFit # ou a pasta onde extraiu o projeto
python3 server.py --init
python3 server.py
```

O servidor escuta na porta **4173**. Abra o endereço do servidor no navegador. O banco é criado automaticamente e os dados permanecem entre reinicializações. Para mudar a porta use `PORT`; para escolher o banco use `DATABASE_PATH`. Veja `.env.example`: as variáveis devem ser exportadas no shell, pois o arquivo .env não é carregado automaticamente.

## Abrir no Windows

Na pasta do projeto, dê dois cliques em **Iniciar EvoFit.bat**. Ele inicia o servidor com o Python instalado e abre o navegador. Mantenha a janela do terminal aberta. O script foi revisado; a execução automatizada foi validada em Linux, não em Windows.

## Treinos em cards

A área Treinos apresenta uma divisão por card, com ilustração e botão **Iniciar treino**. Ao abrir, toque no nome de um exercício: os detalhes abaixo mostram séries, repetições, descanso, instruções e uma ilustração local. Ajuste a carga no campo ou nos botões +/− e clique em **Concluir exercício**. O registro fica salvo no SQLite e pode ser retomado depois de fechar/recarregar a página. Use **Ajustar carga** para corrigir uma conclusão antes de finalizar o treino.

Quando todos os exercícios estiverem concluídos, use **Concluir treino** para gravar o histórico e atualizar o painel do personal. A conclusão é protegida contra repetição de cliques. As ilustrações são diagramas originais de referência, funcionam sem internet e podem ser escolhidas pelo personal no editor. Exercícios sem imagem específica usam a referência genérica.

O personal cria e edita os cards por aluno e acompanha as conclusões parciais. Alterações na prescrição dos exercícios reiniciam o progresso ainda não finalizado daquela divisão; o histórico de treinos completos permanece. Renomeações de título e alterações de imagem preservam o progresso. Se a prescrição mudar enquanto a página está aberta, a aplicação pede para retomar a versão atualizada.

## Atualizar sem perder registros

Siga **COMO ATUALIZAR.txt**: pare o servidor, faça uma cópia de segurança da pasta antiga e copie o código novo sobre essa pasta. **Preserve `evofit.sqlite3`**, que contém os dados. O ZIP não inclui banco de dados e a nova tabela de progresso é criada automaticamente na inicialização. A pasta já baixada no seu computador não recebe mudanças do GitHub automaticamente.

## Contas de demonstração

- Personal: **personal@evofit.demo**
- Aluno: **aluno@evofit.demo**
- Senha de ambas: **EvoFit123!**

As contas estão vinculadas, com treinos, refeições, medidas e histórico fictícios. As contas demo só são inseridas quando o banco está vazio; inicializar novamente não apaga registros.

## Fluxos

O personal seleciona um aluno, cria ou edita treinos por dia/divisão e planos por refeição. Os planos são atribuídos ao aluno selecionado. Em Alunos, cadastra nome, e-mail, objetivo e senha inicial de acesso. O aluno entra com esses dados, consulta os planos, marca os exercícios, registra cargas e conclui o treino. Em Evolução registra peso, cintura, quadril e tórax. Os gráficos e históricos usam os registros reais do banco. O personal consulta esses dados selecionando o aluno. Atualize a página para consultar alterações feitas por outra sessão.

O cadastro livre permite criar personal ou aluno. Um aluno independente não é vinculado automaticamente a um personal; para acompanhamento vinculado, cadastre-o pela área do personal com e-mail ainda não utilizado.

## Validação

```sh
python3 -m unittest discover -s tests -v
node --check static/app.js # verificação adicional, requer Node
```

Os oito testes de integração usam banco temporário e verificam login, cadastro de aluno, criação e edição de treino, atribuição de dieta, registro de treino/cargas/medidas, atualização no personal, edição de perfil, persistência SQLite, logout, credenciais inválidas e isolamento entre usuários e personals. O teste `tests/browser_workouts.py` foi executado com Chromium: cards clicáveis, abertura dos exercícios, carregamento de imagens, ajuste de carga, conclusão por exercício, recarregamento e retomada, histórico completo, sincronização com o personal, escolha de imagem pelo editor, navegação por teclado e largura móvel de 390 px. Não houve erros JavaScript ou falhas de carregamento. O teste usa banco temporário; requer Playwright e Chromium somente para validação, não para usar o app.

Também são testados isolamento de alunos, cargas inválidas, versão desatualizada do plano, progresso após reinicialização, edição de prescrição e conclusão simultânea sem duplicação do histórico.

## Estrutura e persistência

- `server.py`: servidor HTTP, API, permissões, sessões e SQLite.
- `static/`: interface responsiva e ilustrações SVG originais, sem dependências externas.
- `static/workouts.js`: cards, detalhes e controles do fluxo de treino.
- `tests/test_flow.py`: testes de integração.
- `evofit.sqlite3`: banco local, ignorado pelo Git. Contém dados pessoais: não publique esse arquivo.

Faça backup consistente do banco com a API SQLite (ou pare o servidor antes de copiar). O ZIP contém código e documentação, não os dados de usuários. Não exclua o banco para atualizar o código.

## Limitações de implantação

Esta entrega serve ao desenvolvimento e demonstração. O servidor HTTP da biblioteca padrão requer proxy HTTPS e endurecimento antes de exposição pública. Configure `SECURE_COOKIE=1` atrás de HTTPS; implemente limitação de tentativas de login, recuperação de senha, verificação de e-mail, política de dados e backups para produção. Sessões expiram em 24 horas; senhas usam scrypt com salt individual, cookies HttpOnly/SameSite e autorização no servidor. Não há envio de e-mails, sincronização automática, nem serviço de recuperação de senha. Planos alimentares devem ser orientados por profissional habilitado.

A autoria Git usa o nome e e-mail informados por Livia. Isso não constitui assinatura criptográfica de commits nem altera o titular da autenticação GitHub do ambiente.
