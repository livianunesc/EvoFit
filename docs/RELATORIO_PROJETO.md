# EvoFit — relatório do projeto integrado

**Autora:** Livia Nunes Coelho

**Disciplinas:** Desenvolvimento de Websites (DWS), Programação Orientada a Objetos (POO) e Banco de Dados (BD)

**Período de referência:** 4º bimestre de 2026

**Repositório:** https://github.com/livianunesc/EvoFit

## 1. Resumo

O EvoFit é um sistema web de acompanhamento de treinos com dois perfis: personal e aluno. O personal administra alunos, exercícios e fichas de treino; o aluno consulta a prescrição, registra cargas e conclui a atividade. Histórico e ranking permitem acompanhar as conclusões da equipe. A solução integra interface HTML/CSS/JavaScript, rotas Flask, entidades orientadas a objetos, DAOs e persistência MySQL. Um relatório complementar em PHP utiliza PDO para consultar a mesma base.

## 2. Problema e objetivo

O controle de prescrições e conclusões em registros separados dificulta a consulta do treino atual e o acompanhamento dos alunos. O objetivo geral do projeto é centralizar esse fluxo em uma aplicação com autenticação, controle de acesso e persistência relacional.

Objetivos específicos:

- Permitir cadastrar, consultar, atualizar e excluir alunos, exercícios e treinos, respeitando seus vínculos.
- Representar o domínio com classes, encapsulamento, herança, polimorfismo e composição.
- Separar interface, rotas, regras do domínio e persistência por meio do padrão DAO.
- Modelar entidades, cardinalidades, chaves e restrições em um banco relacional normalizado.
- Integrar o front-end ao back-end por Fetch e respostas JSON.
- Produzir consultas SQL comentadas e evidências de funcionamento para a avaliação e a sabatina.

## 3. Escopo e atores

| Ator | Operações |
| --- | --- |
| Personal | Autenticar; gerenciar alunos, catálogo e prescrições; consultar histórico e ranking da equipe; gerar relatório PHP |
| Aluno | Autenticar; consultar seus treinos; informar cargas; concluir uma ficha; consultar seu histórico e o ranking da equipe |

As consultas de alunos, treinos e históricos são limitadas pelo vínculo com o personal. O catálogo de exercícios é compartilhado. A demonstração utiliza contas e registros fictícios.

O sistema registra conclusões informadas pelo aluno; não mede execução física. A soma de cargas apresentada no histórico não representa volume de treino. A versão acadêmica não inclui acompanhamento nutricional nem retomada parcial persistida.

## 4. Arquitetura e desenvolvimento

A aplicação adota a separação descrita no material de POO do 4º bimestre:

1. **Interface:** `index.html` e `pages/` estruturam as telas. `css/estilo.css` define o layout responsivo. `js/api.js` e `js/app.js` tratam eventos, Fetch, JSON e atualização do DOM.
2. **Rotas:** `app.py` recebe requisições GET, POST, PUT e DELETE, verifica a sessão e o perfil e devolve respostas JSON.
3. **Domínio:** `models.py` contém `Usuario`, `Personal`, `Aluno`, `Exercicio`, `ItemTreino` e `Treino`, com validação dos atributos e comportamentos.
4. **Persistência:** `dao.py` contém a conexão e os DAOs; consultas parametrizadas e transações preservam a integridade das operações compostas.
5. **Banco:** `banco/schema.sql` cria as tabelas e restrições MySQL. `banco/dados_teste.sql` complementa os exemplos utilizados nas consultas da avaliação.
6. **Módulo PHP:** `/relatorio-php` exige sessão de personal e executa um processo PHP CLI. O relatório usa PDO, consulta parametrizada e saída HTML com escape.

O fluxo completo está representado em [ARQUITETURA.md](ARQUITETURA.md). Os diagramas de classes, entidade-relacionamento e sequência estão em [MODELAGEM.md](MODELAGEM.md).

## 5. Modelagem e regras de integridade

O modelo utiliza cinco tabelas: `usuarios`, `exercicios`, `treinos`, `treino_exercicios` e `registros`. A tabela associativa `treino_exercicios` resolve a relação N:N entre fichas e exercícios. Séries, repetições, cargas e descanso pertencem à prescrição, e não ao cadastro geral de um exercício.

As chaves primárias identificam cada registro; as estrangeiras vinculam personal, aluno, treino e exercício. As restrições impedem excluir dados necessários ao histórico. O aluno de um treino com conclusões não pode ser alterado. A data da conclusão é armazenada como `DATETIME` em UTC.

A gravação de uma ficha e seus itens ocorre em uma transação. A conclusão também usa transação e uma chave única de idempotência para impedir duplicação por reenvio. O hash da prescrição permite rejeitar uma ficha desatualizada com HTTP 409 antes de registrar a atividade.

## 6. Consultas de Banco de Dados

O arquivo `banco/consultas_avaliacao.sql` reúne 14 consultas comentadas, relacionadas aos critérios do Apêndice B da apostila de BD do 4º bimestre:

- INNER JOIN, LEFT JOIN e associação de quatro tabelas para consultar fichas e exercícios.
- Identificação de alunos, exercícios e treinos sem correspondência.
- Agregações, agrupamentos e subconsultas escalares com AVG, MAX e MIN.
- Subconsultas com IN, EXISTS e NOT EXISTS.
- Paginação com ORDER BY estável e LIMIT/OFFSET.
- Consulta de auditoria das regras de perfil e relacionamento.

As perguntas respondidas, os filtros, a finalidade das subconsultas e o cálculo da paginação estão descritos nos comentários SQL. As evidências de execução estão na modelagem e no relatório de validação.

## 7. Resultados e validação

A integração foi executada com MySQL 8.4, Python 3.12/Flask e PHP 8.2/PDO em Linux. A suíte acadêmica passou em 11 testes, incluindo autenticação, autorização por equipe, CRUD, rollback, idempotência concorrente e rejeição de prescrição desatualizada. As duas interfaces passaram em testes de navegador, incluindo largura móvel de 375 px. As 14 consultas SQL foram executadas, e a repetição dos dados complementares preservou as contagens.

Procedimentos, comandos, resultados e limites do ambiente estão em [VALIDACAO_ACADEMICA.md](VALIDACAO_ACADEMICA.md). A execução nativa dos scripts Windows e a compatibilidade MariaDB não foram verificadas nessa rodada.

## 8. Correspondência com as etapas da entrega

| Etapa do documento de orientação | Artefatos e evidências |
| --- | --- |
| 1 — UML revisado, tabelas e conexão com o banco | `docs/MODELAGEM.md`, `banco/schema.sql`, conexão `BancoDados` e consulta de saúde |
| 2 — Python com classes, DAOs, rotas Flask e cadastro/consulta | `models.py`, `dao.py`, `app.py` e testes de integração |
| Final — HTML/CSS/JS consumindo Flask por Fetch e aplicação integrada | `index.html`, `pages/`, `css/`, `js/` e testes de navegador |
| Banco de Dados AV2 — modelo, JOINs, subqueries, paginação e documentação | Scripts em `banco/`, diagramas e resultados documentados |
| Apresentação e sabatina | Fluxos completos, interface `/apresentacao/` e roteiro de demonstração |

A matriz detalhada com as páginas dos materiais está em [REQUISITOS_AVALIACAO.md](REQUISITOS_AVALIACAO.md). Os prazos definidos no documento de orientação são 09/11/2026, 13/11/2026 e 17/11/2026; esta tabela descreve os artefatos, sem afirmar submissão nas datas anteriores.

O repositório contém o código e seu histórico. O documento de orientação também exige o professor como colaborador; a confirmação do convite ocorre nas configurações do GitHub.

## 9. Conclusão

O EvoFit integra os conteúdos das três disciplinas em um fluxo de cadastro, prescrição e registro de treinos. A separação em camadas relaciona os objetos do domínio às rotas e ao banco, enquanto as consultas comentadas demonstram os relacionamentos e os critérios de BD. A validação confirma a execução dos fluxos documentados no ambiente de testes.

## Referências

- **COMECE AQUI! (PROJETO).** Projeto Integrado — DWS + POO + BD: etapas de entrega e instruções de submissão via GitHub. 2026, p. 1–2.
- **Apostila POO — 4º bimestre — UNASP.** Padrão DAO, Flask, JSON e integração com Fetch. 2026.
- **Apostilas POO — 1º, 2º e 3º bimestres — UNASP.** Classes, encapsulamento, herança, polimorfismo, análise e UML.
- **Apostilas DWS — 1º ao 4º bimestres.** HTML, CSS, JavaScript, PHP, integração REST e organização do projeto.
- **Apostila Banco de Dados ER Completa** e **Banco de Dados — 2º bimestre.** Modelagem, cardinalidades, chaves e normalização.
- **Apostila Banco de Dados — 3º bimestre.** Manipulação, filtros, ordenação e agregações SQL. 2026.
- **Apostila Banco de Dados — 4º bimestre, v2.** JOINs, subqueries, paginação e rubrica AV2, p. 30 e 38. 2026.
