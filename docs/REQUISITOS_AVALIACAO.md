# EvoFit — especificação de requisitos e rastreabilidade da avaliação

**Autora:** Livia Nunes Coelho

**Projeto:** EvoFit — acompanhamento de treinos e evolução em equipe

**Disciplinas:** Desenvolvimento de Websites (DWS), Programação Orientada a Objetos (POO) e Banco de Dados (BD)

**Referência curricular:** Projeto Integrado — 4º bimestre de 2026

## 1. Objetivo e escopo

O EvoFit é um sistema web para organizar o acompanhamento de alunos por um personal, manter um catálogo de exercícios, prescrever fichas de treino e registrar conclusões com as cargas utilizadas. O histórico e o ranking apresentam os resultados da equipe, respeitando os vínculos entre as contas.

O sistema utiliza HTML5 na estrutura das páginas, CSS3 na apresentação responsiva, JavaScript na interação e no consumo da API, Python com Flask e orientação a objetos no back-end, MySQL na persistência e PHP com PDO na geração de um relatório complementar. O relatório PHP é acessado por uma rota autenticada do Flask. A versão de apresentação concentra login, consulta de treinos, conclusão, histórico e ranking em uma única página, utilizando a mesma API e o mesmo banco.

A organização segue o fluxo de análise e implementação desenvolvido nas disciplinas: requisitos, classes e relacionamentos, modelo relacional, DAOs, rotas HTTP e interface integrada por Fetch.

## 2. Referências e critérios de entrega

As páginas citadas correspondem à posição no arquivo PDF, contando a capa. Os identificadores abaixo são utilizados nas tabelas de rastreabilidade.

| Identificador | Documento de referência | Conteúdo utilizado |
| --- | --- | --- |
| GUIA | `COMECE AQUI! (PROJETO).pdf`, p.1–2 | Composição do projeto, etapas, prazos e entrega via GitHub |
| BD-ER | `Apostila_Banco_de_Dados_ER_Completa (1).pdf`, p.4,6–17,27–29 | Entidades, atributos, chaves, cardinalidade e passagem ao modelo físico |
| BD-2 | `Apostila_Banco_de_Dados 2ºBim.pdf`, p.10–32 | Tipos, constraints, normalização, relacionamentos e CRUD |
| BD-3 | `Apostila_Banco_de_Dados_3Bimestre_2026.pdf`, p.4–22 | Manipulação SQL, filtros, ordenação e agregações |
| BD-4 | `Apostila_2_Ano_Banco_de_Dados_4_Bimestre_2026_v2.pdf`, p.9–25,30,38 | JOINs, subqueries, paginação, documentação e rubrica AV2 |
| POO-1 | `Apostila_POO_1Bimestre_UNASP.pdf`, p.4–16 | Fundamentos Python, classes, métodos, modularização e encapsulamento |
| POO-2 | `Apostila_POO_2Bimestre_UNASP.pdf`, p.3–13 | Abstração, herança, polimorfismo, exceções e análise OO |
| POO-3 | `Apostila_POO_3Bimestre_UNASP (1).pdf`, p.2–9 | Requisitos funcionais e não funcionais, UML, sequência e implementação |
| POO-4 | `Apostila_POO_4Bimestre_UNASP.pdf`, p.7–15 | Persistência com DAO, Flask, JSON e integração com Fetch |
| DWS-1 | `DWS_Apostila_1Bimestre.pdf`, capítulos 1–6 | HTML semântico, CSS, JavaScript, condições, listas e funções |
| DWS-2 | `DWS_Apostila_2Bimestre.pdf`, p.3–18 | DOM, eventos, Fetch, PHP, formulários, MySQL e CRUD |
| DWS-3 | `DWS_Apostila_3Bimestre.pdf`, p.3–14 | Planejamento, páginas, organização, responsividade e PHP/PDO |
| DWS-4 | `DWS_Apostila_4Bimestre.pdf`, p.7–10,14 | Flask e Fetch, CRUD HTTP, validação, experiência de uso e versionamento |

O GUIA estabelece a entrega integrada com back-end Python orientado a objetos, DAOs e Flask; banco de dados funcional; e front-end HTML/CSS/JavaScript consumindo as rotas com Fetch. A rubrica AV2 de BD-4, páginas 30 e 38, especifica os critérios de modelagem, consultas, paginação, documentação e sabatina. Os conteúdos dos demais bimestres fundamentam as decisões de implementação.

### 2.1 Etapas previstas no guia do projeto

| Etapa | Prazo estabelecido | Produto previsto |
| --- | --- | --- |
| Etapa 1 | 09/11/2026 | Diagrama de classes/UML revisado, estrutura das tabelas criada e conexão inicial com o banco |
| Etapa 2 | 13/11/2026 | Classes, DAOs e rotas Flask; operações de cadastro e consulta funcionando |
| Entrega final | 17/11/2026 | Sistema integrado de ponta a ponta, com HTML/CSS/JavaScript, Fetch e preparação para apresentação |

### 2.2 Requisitos da entrega integrada

| ID | Fonte | Requisito | Arquivos e evidências |
| --- | --- | --- | --- |
| INT-01 | GUIA, p.1 | Código completo do sistema e banco | `index.html`, `pages/`, `css/`, `js/`, `app.py`, `models.py`, `dao.py` e `banco/` |
| INT-02 | GUIA, p.2; POO-4, p.11 | Diagrama de classes/UML coerente com a implementação | `docs/MODELAGEM.md`: classes, atributos, métodos, visibilidade, multiplicidades e relacionamentos |
| INT-03 | GUIA, p.2 | Tabelas criadas e conexão inicial funcionando | `banco/schema.sql`; conexão e inicialização em `dao.py`; resultados em `docs/VALIDACAO_ACADEMICA.md` |
| INT-04 | GUIA, p.2; POO-4, p.7–8,12–13 | Classes de domínio, DAOs e rotas Flask | `models.py`, `dao.py`, `app.py` e `tests/test_academico.py` |
| INT-05 | GUIA, p.2; DWS-4, p.7–9 | Front-end consumindo Flask por Fetch | `js/api.js`, `js/app.js`, `index.html`, `pages/` e testes de navegador |
| INT-06 | GUIA, p.1 | Disponibilização do código em repositório GitHub e inclusão do professor como colaborador | Repositório `livianunesc/EvoFit`, branch `main`; situação do convite registrada na seção 8 |
| INT-07 | GUIA, p.1; DWS-4, p.10,14 | Histórico regular de commits descritivos | Histórico de versionamento do repositório |

## 3. Requisitos funcionais e casos de uso

| ID | Ator | Requisito funcional | Rotas Flask e métodos |
| --- | --- | --- | --- |
| RF-01 | Personal e aluno | Autenticar, consultar a sessão e encerrar o acesso | `POST /api/login`, `GET /api/sessao`, `POST /api/logout` |
| RF-02 | Personal | Cadastrar, consultar, editar e excluir alunos da própria equipe | `GET/POST /api/alunos`, `PUT/DELETE /api/alunos/<id>` |
| RF-03 | Personal | Manter o catálogo de exercícios | `GET/POST /api/exercicios`, `PUT/DELETE /api/exercicios/<id>` |
| RF-04 | Personal | Prescrever e revisar fichas com exercícios, séries, repetições, carga e descanso | `GET/POST /api/treinos`, `PUT/DELETE /api/treinos/<id>` |
| RF-05 | Aluno | Consultar seus treinos e registrar uma conclusão com as cargas utilizadas | `GET /api/treinos`, `POST /api/treinos/<id>/concluir` |
| RF-06 | Personal e aluno | Consultar histórico e ranking no escopo autorizado | `GET /api/historico`, `GET /api/ranking` |
| RF-07 | Personal | Gerar relatório complementar da equipe em PHP | `GET /relatorio-php` |

### 3.1 Regras de negócio

- O personal altera somente alunos e treinos da própria equipe. O aluno conclui somente seus próprios treinos.
- Cada ficha contém de um a trinta exercícios válidos, sem repetir o mesmo exercício na prescrição.
- Séries, repetições, carga e descanso pertencem à prescrição; nome, grupo muscular e instruções pertencem ao catálogo.
- Um aluno com treinos, um exercício prescrito ou uma ficha com histórico possuem vínculos protegidos contra exclusão.
- A edição de uma ficha não transfere seu histórico para outro aluno. A soma histórica das cargas permanece registrada no evento de conclusão.
- A conclusão utiliza uma chave de idempotência: o reenvio da mesma operação não cria outra pontuação.
- Uma prescrição alterada após a consulta do aluno exige a atualização da ficha antes de uma nova conclusão. O campo `versao` identifica os parâmetros prescritos.
- A carga total registrada corresponde à soma das cargas informadas; não representa volume de treinamento.

### 3.2 Fluxo do caso de uso “Prescrever treino”

1. O personal preenche o formulário e seleciona o aluno e os exercícios.
2. JavaScript valida os campos e envia JSON por Fetch.
3. Flask verifica a sessão, o perfil e os dados recebidos.
4. As classes `Treino` e `ItemTreino` validam a prescrição.
5. `TreinoDAO` verifica os vínculos e grava a ficha e seus itens em uma transação.
6. Após a confirmação, a interface consulta novamente a listagem e apresenta o resultado.

O fluxo corresponde ao encadeamento interface → rota → modelo/DAO → MySQL, conforme POO-3, páginas 2–9, e POO-4, páginas 11–15.

## 4. Requisitos não funcionais

| ID | Qualidade | Requisito e evidência |
| --- | --- | --- |
| RNF-01 | Segurança | Hash de senha, sessão autenticada, autorização no servidor, parâmetros SQL e escape de saída em `app.py`, `dao.py`, `js/app.js` e `php_academico/relatorio.php` |
| RNF-02 | Usabilidade e acessibilidade | HTML semântico, labels, navegação por teclado, validação, mensagens visíveis e layout responsivo em `index.html`, `pages/`, `css/estilo.css` e `js/app.js` |
| RNF-03 | Consistência | Transações da prescrição, constraints, chave única da conclusão e verificação de versão em `dao.py` e `banco/schema.sql` |
| RNF-04 | Manutenção e portabilidade | Separação entre páginas, estilos, scripts, modelos, DAOs e rotas; dependências e inicialização documentadas no `README.md` |

A persistência utiliza MySQL com instruções parametrizadas. O driver Python utiliza `%s`; o PDO utiliza parâmetros associados na preparação da consulta. Os valores de formulários são fornecidos separadamente ao SQL.

## 5. Rastreabilidade da rubrica AV2 de Banco de Dados

| ID | Fonte | Critério | Arquivos e evidências |
| --- | --- | --- | --- |
| BD-01 | BD-4, p.30,38; BD-ER, p.27–29 | Modelo com PK, FK e relacionamentos coerentes | `banco/schema.sql` e diagramas em `docs/MODELAGEM.md` |
| BD-02 | BD-4, p.30 | Dados de teste com registros sem correspondência | Seed de `app.py`, `banco/dados_teste.sql`: aluno sem treino, exercício sem prescrição e treino sem conclusão |
| BD-03 | BD-4, p.9–16,30,38 | INNER JOIN, LEFT JOIN e JOIN de três ou mais tabelas | Consultas 1–4 de `banco/consultas_avaliacao.sql` |
| BD-04 | BD-4, p.17–21,30,38 | Subqueries escalares com AVG/MAX/MIN e uso de IN ou EXISTS | Consultas 5–10 de `banco/consultas_avaliacao.sql` |
| BD-05 | BD-4, p.22–23,30,38 | ORDER BY estável, LIMIT e OFFSET correto | Consultas 11–12: duas páginas do mesmo histórico; desempate por ID e cálculo `(pagina - 1) * tamanho` |
| BD-06 | BD-4, p.24–25,30,38 | Script, dados e consultas organizadas e comentadas | `banco/schema.sql`, `banco/dados_teste.sql` e `banco/consultas_avaliacao.sql` |
| BD-07 | BD-4, p.25,30,38 | Conferência dos resultados e preparação para sabatina | Evidências em `docs/MODELAGEM.md`, `docs/VALIDACAO_ACADEMICA.md` e roteiro em `docs/ROTEIRO_APRESENTACAO.md` |

### 5.1 Índice das consultas comentadas

| Consulta | Pergunta ou conceito demonstrado |
| --- | --- |
| 1 | Treinos dos alunos da equipe com INNER JOIN |
| 2 | Alunos com e sem treino, utilizando LEFT JOIN e contagem |
| 3 | Ficha de exercícios por aluno, com JOIN de quatro tabelas |
| 4 | Exercícios do catálogo sem prescrição |
| 5 | Conclusões com carga acima da média da equipe — AVG |
| 6 | Conclusões com a maior carga da equipe — MAX, preservando empates |
| 7 | Conclusões com a menor carga da equipe — MIN |
| 8 | Alunos que concluíram treino — IN |
| 9 | Treinos com histórico — EXISTS |
| 10 | Treinos sem conclusão — NOT EXISTS |
| 11–12 | Primeira e segunda páginas do histórico com a mesma ordenação |
| 13 | Filtro no ON de LEFT JOIN, preservando alunos sem conclusão no período |
| 14 | Auditoria dos papéis nos vínculos de personal, aluno e treino |

A rubrica de BD-4, página 38, organiza a avaliação em seis critérios: **modelo, JOINs, subqueries, paginação, documentação e sabatina**. O nível “Excelente” descreve relações coerentes; escolha correta e explicada dos JOINs; subqueries escalares e IN/EXISTS com propósito; ordenação estável e deslocamento correto; consultas comentadas e entrega organizada; explicação e modificação autônomas do código.

## 6. Rastreabilidade dos conteúdos de DWS e POO

| Conteúdo | Fonte | Evidência na implementação |
| --- | --- | --- |
| HTML semântico, formulário e estrutura de páginas | DWS-1, capítulos 1–2; DWS-3, p.5–6; DWS-4, p.8 | `index.html` e `pages/`: idioma, viewport, cabeçalho, navegação, conteúdo principal, labels e rodapé |
| Responsividade e organização dos estilos | DWS-3, p.7–8; DWS-4, p.8 | `css/estilo.css`: variáveis, Flexbox/Grid e media queries |
| Eventos, DOM, JSON e Fetch | DWS-2, p.3–7; DWS-3, p.9–10; DWS-4, p.7–9 | `js/api.js` e `js/app.js`: eventos, requisições e atualização segura da listagem |
| CRUD HTTP, validação e retorno visual | DWS-4, p.9–10 | Formulários com GET/POST/PUT/DELETE, campos obrigatórios e mensagens de processamento, sucesso e erro |
| PHP, MySQL e PDO | DWS-2, p.8–18; DWS-3, p.13–14 | `php_academico/relatorio.php`: conexão PDO, consulta parametrizada, agregações e HTML escapado |
| Classes, métodos e encapsulamento | POO-1, p.11–16 | `models.py`: propriedades com validação e métodos do domínio |
| Abstração, herança e polimorfismo | POO-2, p.3–9 | `Usuario` abstrata; subclasses `Personal` e `Aluno`; método `pode_prescrever()` aplicado à autorização |
| Composição e relacionamentos | POO-2, p.12–13; POO-3, p.5–9 | `Treino` composto por `ItemTreino`; UML em `docs/MODELAGEM.md` |
| Exceções e separação de responsabilidades | POO-2, p.10–11; POO-4, p.12–13 | `ErroDominio`, DAOs e tratamento das respostas em `app.py` |
| Persistência e padrão DAO | POO-4, p.7–8,12–13 | `dao.py`: conexão, transações, consultas e gravações separadas das entidades |
| Flask e integração JSON | POO-4, p.9–15 | `app.py`, `js/api.js` e testes da API e do navegador |
| Tipos, integridade e normalização | BD-2, p.10–27 | `banco/schema.sql` e justificativas de 1FN, 2FN e 3FN em `docs/MODELAGEM.md` |
| Manipulação, filtros e agregações SQL | BD-2, p.28–32; BD-3, p.4–22 | DAOs e consultas comentadas em `banco/consultas_avaliacao.sql` |

## 7. Documentos e evidências do projeto

| Artefato | Localização | Finalidade |
| --- | --- | --- |
| Instruções de instalação e execução | `README.md` | Preparação do ambiente e inicialização |
| Modelo de classes e banco | `docs/MODELAGEM.md` | UML, ER, dicionário e decisões de modelagem |
| Estrutura, dados e consultas | `banco/` | Scripts SQL da avaliação |
| Testes de entidades e integração | `tests/test_academico.py` | Regras do domínio, API e persistência |
| Testes da interface principal | `tests/browser_academico.py` | Operações completas pela interface |
| Testes da versão de apresentação | `tests/browser_apresentacao_academica.py` | Fluxo reduzido integrado ao banco |
| Resultados da validação | `docs/VALIDACAO_ACADEMICA.md` | Comandos, resultados e limites registrados |
| Roteiro de apresentação | `docs/ROTEIRO_APRESENTACAO.md` | Sequência para demonstração e sabatina |
| Versão reduzida | `apresentacao/` | Demonstração em uma página com persistência real |
| Relatório PHP | `php_academico/` | Consulta e geração HTML por PDO |

Na apresentação, a sequência prevista é: descrever o problema; demonstrar cadastro, consulta, edição e exclusão; seguir uma requisição do formulário ao DAO; comprovar persistência; explicar PK/FK e cardinalidades; executar JOINs e subqueries; calcular o OFFSET; e apresentar a participação do PHP na arquitetura.

## 8. Situação de disponibilização e apresentação

| Item | Situação |
| --- | --- |
| Código no GitHub | Disponibilizado no repositório `livianunesc/EvoFit`, branch `main` |
| Professor como colaborador | Não verificado |
| Apresentação oral e sabatina | A realizar |

O GUIA, página 1, estabelece a inclusão do professor como colaborador pelo endereço `leonardo.stephan@eaportal.org`. A apresentação deverá demonstrar o funcionamento integrado e a explicação das decisões de modelagem, consultas e código, conforme a rubrica de Banco de Dados.
