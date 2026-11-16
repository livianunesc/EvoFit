# EvoFit — roteiro de apresentação e sabatina

**Autora:** Livia Nunes Coelho

**Disciplinas:** DWS, POO e Banco de Dados

**Referências:** COMECE AQUI! (PROJETO), p. 1–2; rubrica AV2 de BD, p. 30 e 38.

## 1. Objetivo da demonstração

Apresentar a integração entre front-end HTML/CSS/JavaScript, rotas Flask, classes e DAOs Python e banco MySQL. A demonstração contempla as operações do sistema, a modelagem e as consultas exigidas na avaliação de BD.

## 2. Preparação do ambiente

1. Iniciar com `python tools/docker_academico.py iniciar --abrir` ou com os scripts Windows e MySQL local. O inicializador abre `index.html` após verificar a disponibilidade do servidor e do banco.
2. Confirmar o login das contas fictícias e abrir o banco `evofit_academico` no cliente SQL.
3. Importar `banco/dados_teste.sql` após a inicialização para disponibilizar os casos sem correspondência e a paginação.
4. Abrir os diagramas de `MODELAGEM.md`, os scripts SQL e os arquivos `models.py`, `dao.py`, `app.py` e `js/api.js`.
5. Manter os arquivos de credenciais e chaves fora da área de exibição.

A execução local requer servidor e MySQL ativos. Os recursos da interface são locais; a preparação inicial precisa dos pacotes e imagens descritos no README.

## 3. Demonstração funcional principal

| Passo | Operação demonstrada | Evidência |
| --- | --- | --- |
| 1 | Autenticar como personal | Sessão e painel da equipe |
| 2 | Cadastrar e editar aluno com e-mail exclusivo | POST, GET e PUT com resultado persistido |
| 3 | Cadastrar exercício e revisar instruções | Catálogo e atualização no banco |
| 4 | Prescrever treino com séries, repetições, carga e descanso | Entidade associativa e transação |
| 5 | Entrar como aluno e consultar a ficha | Controle por perfil e proprietário |
| 6 | Marcar exercícios, preencher cargas e concluir | POST com versão da prescrição e chave idempotente |
| 7 | Consultar histórico e ranking e recarregar | Persistência da conclusão no MySQL |
| 8 | Voltar ao personal e abrir o relatório PHP | Integração Flask/PHP e consulta PDO |
| 9 | Excluir cadastro descartável e tentar exclusão com vínculo | DELETE e proteção de integridade |

Os registros utilizados na apresentação são fictícios. A consulta do histórico e a atualização da listagem demonstram o retorno completo do fluxo interface → API → banco → interface.

## 4. Demonstração reduzida

A página `/apresentacao/` concentra o fluxo em aproximadamente três minutos:

1. Apresentar os perfis e as responsabilidades das camadas.
2. Autenticar `aluno@evofit.demo` com a senha de demonstração `EvoFit123!`.
3. Selecionar o treino, apresentar a prescrição e informar as cargas.
4. Marcar todos os exercícios e registrar a conclusão.
5. Exibir histórico e ranking, recarregar e confirmar a persistência.
6. Encerrar a sessão e indicar as páginas de cadastro da aplicação principal.

A interface reduzida utiliza as mesmas rotas e tabelas da aplicação principal.

## 5. Demonstração dos conceitos de POO

| Conceito | Implementação no EvoFit |
| --- | --- |
| Abstração | `Usuario` representa os atributos e comportamentos comuns |
| Herança | `Personal` e `Aluno` especializam `Usuario` |
| Encapsulamento | Propriedades validam nome, e-mail e objetivo |
| Polimorfismo | `pode_prescrever()` responde conforme o perfil e participa da autorização |
| Composição | `Treino` reúne objetos `ItemTreino` |
| DAO | Classes próprias executam as operações SQL de cada entidade |
| Exceções e transações | Falhas de domínio ou integridade interrompem a operação; gravações compostas têm rollback |

Uma operação de cadastro permite acompanhar `submit` em `js/app.js`, a chamada Fetch em `js/api.js`, a rota Flask, a criação do objeto, a chamada ao DAO e o INSERT parametrizado.

## 6. Consultas e conceitos da sabatina de BD

| Critério | Demonstração e justificativa |
| --- | --- |
| Modelo | Localizar PK `treinos.id`, FK `treinos.aluno_id` e referência a `usuarios.id` |
| Associação N:N | Relacionar as tabelas `treinos`, `treino_exercicios` e `exercicios` |
| Normalização | Justificar carga na prescrição e proprietário do histórico derivado do treino |
| INNER JOIN e LEFT JOIN | Comparar consultas com e sem alunos sem treino; explicar a condição ON |
| Contagem | Comparar COUNT(t.id) e COUNT(*) no caso sem correspondência |
| JOIN de três ou mais tabelas | Executar a consulta 3 e acompanhar aluno → treino → prescrição → exercício |
| Subquery escalar | Executar AVG/MAX/MIN isoladamente e depois a consulta externa |
| IN e EXISTS | Diferenciar comparação com conjunto e verificação de existência |
| Paginação | Calcular `(pagina - 1) * tamanho`, executar duas páginas e justificar o desempate por ID |
| Alterações seguras | Explicar parâmetros SQL, WHERE, integridade referencial e rollback |

Os comentários de `banco/consultas_avaliacao.sql` registram a pergunta, a estratégia e a ordenação de cada consulta. A sabatina inclui execução, explicação dos resultados e modificação de filtros.

## 7. Limites técnicos da solução

O sistema registra conclusões informadas pelo aluno e soma de cargas; não mede execução física e não calcula volume por repetição. Não mantém retomada parcial persistida. O histórico usa o título atual da ficha. O catálogo de exercícios é compartilhado, enquanto os dados de alunos e seus treinos têm escopo de equipe.

## 8. Registro da entrega

O código e seu histórico estão em `livianunesc/EvoFit`, branch `main`. O documento de orientação exige o professor como colaborador pelo e-mail `leonardo.stephan@eaportal.org`; o estado do convite deve ser conferido no GitHub. A apresentação e a sabatina constituem a etapa presencial prevista na avaliação.
