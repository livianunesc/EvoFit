# EvoFit — projeto integrado DWS + POO + Banco de Dados

**Autora:** Livia Nunes Coelho

**Disciplinas:** Desenvolvimento de Websites, Programação Orientada a Objetos e Banco de Dados

**Repositório:** [livianunesc/EvoFit](https://github.com/livianunesc/EvoFit)

Sistema fitness em português para personal cadastrar alunos, organizar exercícios e prescrever treinos. O aluno consulta sua ficha, informa as cargas, conclui o treino e acompanha histórico e ranking da própria equipe.

O projeto implementa a integração definida em **COMECE AQUI! (PROJETO)**: back-end **Python orientado a objetos com Flask e DAOs**, banco **MySQL** e front-end **HTML, CSS e JavaScript**, que consome as rotas Flask por **Fetch**. O módulo **PHP/PDO** gera um relatório complementar da equipe e compartilha a mesma base de dados.

O [relatório do projeto](docs/RELATORIO_PROJETO.md) apresenta o problema, os objetivos, a solução e os resultados. A [matriz de requisitos](docs/REQUISITOS_AVALIACAO.md) relaciona as etapas de entrega e a rubrica de Banco de Dados aos arquivos e às evidências do sistema.

## Iniciar com Docker (recomendado)

Requisitos: Python 3.10+ e Docker com Compose 2.24.4+ em execução. Não precisa instalar PHP ou MySQL no computador.

```sh
python tools/docker_academico.py iniciar
```

A preparação cria `.env.academico` com uma senha aleatória local, constrói a imagem quando necessário, inicia MySQL, cria as tabelas/dados fictícios somente em banco vazio e verifica conexão e HTML. O arquivo local e os volumes preservam a configuração e os dados entre reinicializações.

No computador local, abra a porta **4173** no navegador. O sistema precisa do servidor: não abra o `index.html` por `file://` e não use somente Live Server.

- Principal: `/`.
- Versão curta para apresentação: `/apresentacao/`.
- Relatório PHP: `/relatorio-php`, após entrar como personal.

Contas fictícias do banco novo:

| Perfil | E-mail | Senha de demonstração |
| --- | --- | --- |
| Personal | personal@evofit.demo | EvoFit123! |
| Aluno | aluno@evofit.demo | EvoFit123! |

Para parar sem apagar dados:

```sh
python tools/docker_academico.py parar
```

Use `iniciar --rebuild` após mudar dependências ou o Dockerfile. O código é montado no container; após alterações em Python, reinicie o serviço app, pois o modo debug está desativado. HTML/CSS/JS atualizam ao recarregar.

## Rodar com Python e MySQL local (XAMPP ou Linux)

Requisitos: Python 3.10+, MySQL 8.0.16+ ou MariaDB 10.4+. Para o relatório, PHP 8.2+ com PDO MySQL. As validações desta entrega foram feitas com MySQL 8.4 em Linux; os scripts Windows não foram executados nativamente.

No Windows, inicie MySQL no XAMPP e use `Preparar EvoFit.bat`, depois `Iniciar EvoFit.bat`. Se o MySQL usa senha/porta diferente, configure `.env.academico` antes de repetir a preparação.

Por terminal:

```sh
python -m venv .venv
# Linux/macOS:
. .venv/bin/activate
# Windows PowerShell, em vez do comando anterior:
# .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tools/preparar_academico.py --local
# Confira DB_* no .env.academico, sem publicar credenciais.
python app.py init-db --create-database
python server.py
```

A criação do banco requer permissão MySQL. Se ele já foi criado, use `python app.py init-db` sem `--create-database`. O schema não altera tabelas antigas nem apaga registros; não é um mecanismo de migração estrutural. As contas demo só são inseridas em banco sem usuários. Configure `PHP_BIN` quando PHP não estiver no PATH (ex.: `C:\xampp\php\php.exe`).

## Organização do projeto

| Arquivo/pasta | Responsabilidade |
| --- | --- |
| `index.html`, `pages/` | HTML semântico, formulários, navegação e tabelas |
| `css/estilo.css` | Layout, identidade visual e media queries |
| `js/api.js`, `js/app.js` | DOM, eventos, validação e Fetch GET/POST/PUT/DELETE |
| `models.py` | Entidades; encapsulamento, herança, abstração, polimorfismo e composição |
| `dao.py` | Conexão, DAOs, SQL parametrizado e transações |
| `app.py`, `server.py` | Rotas Flask, autenticação, JSON e entrada do servidor |
| `banco/schema.sql` | Modelo físico normalizado, PK, FK, UNIQUE e CHECK |
| `banco/dados_teste.sql` | Casos complementares, inclusive dados sem correspondência |
| `banco/consultas_avaliacao.sql` | 14 consultas comentadas: JOIN, subqueries e paginação |
| `php_academico/relatorio.php` | Relatório PDO real, executado por CLI após autenticação Flask |
| `apresentacao/` | Interface reduzida, mesma API e banco real |
| `docs/REQUISITOS_AVALIACAO.md` | Requisitos funcionais/não funcionais, casos de uso e rastreabilidade da avaliação |
| `docs/MODELAGEM.md` | UML, ER, sequência, dicionário de dados e normalização |
| `docs/RELATORIO_PROJETO.md` | Relatório técnico do projeto integrado |
| `docs/ROTEIRO_APRESENTACAO.md` | Passo a passo e perguntas para a sabatina |

O fluxo de uma operação é **HTML → evento JavaScript → Fetch → rota Flask → objeto → DAO → MySQL → JSON → DOM**. Os comentários no código registram as responsabilidades de cada camada e as regras do domínio.

## Funcionalidades e regras

- Personal: CRUD de alunos, catálogo de exercícios e prescrição de treinos; histórico/ranking da própria equipe; relatório PHP.
- Aluno: seus treinos, preenchimento de cargas, conclusão, histórico e ranking da própria equipe. Contas independentes não veem outras equipes.
- A prescrição usa uma tabela associativa: treino N:N exercício. Séries, repetições, carga e descanso pertencem à associação.
- A interface exige marcar todos os exercícios antes de concluir; a API exige uma carga válida por exercício. Não há sensor para comprovar atividade física.
- Uma versão da prescrição detecta ficha desatualizada: se o personal alterar exercícios/cargas, a API exige recarregar antes de concluir.
- A chave única de conclusão impede duplicação por reenvio da mesma tentativa. Uma nova sessão/ação de treino recebe nova chave e pode gerar outro registro.
- O histórico guarda a data UTC e a soma das cargas informadas, em kg. Essa soma **não é volume de treino** e não substitui acompanhamento profissional.
- Não se exclui aluno com treinos, exercício em uso ou treino com histórico. O dono de treino com histórico não pode mudar. A API devolve conflito, preservando os vínculos.
- O catálogo é compartilhado entre os personais. Dados pessoais, treinos e históricos têm escopo por equipe.

A edição acadêmica concentra o fluxo de treino. O histórico guarda título pelo vínculo ao treino e soma de cargas, sem snapshot por exercício nem retomada parcial persistida; alterações do título são refletidas em consultas posteriores. A edição anterior, mais extensa, permanece preservada para referência.

## Banco e consultas da avaliação

Depois do `init-db`, importe `banco/dados_teste.sql` e execute `banco/consultas_avaliacao.sql` no banco **evofit_academico** pelo MySQL Workbench/phpMyAdmin. No terminal Docker, sem imprimir credenciais:

```sh
docker compose --env-file .env.academico -p evofit-academico -f compose.academico.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"' < banco/dados_teste.sql
docker compose --env-file .env.academico -p evofit-academico -f compose.academico.yaml exec -T db sh -c 'MYSQL_PWD="$MYSQL_PASSWORD" mysql -u"$MYSQL_USER" "$MYSQL_DATABASE"' < banco/consultas_avaliacao.sql
```

Os comandos acima usam redirecionamento de Bash/CMD. Em outros terminais, use o cliente gráfico para importar os arquivos. As variáveis de sessão nas consultas SQL são para estudo; a API usa IDs da sessão autenticada e parâmetros do DAO.

## Testar sem tocar no banco de demonstração

```sh
python tools/docker_academico.py iniciar --testes
python tools/docker_academico.py validar --testes
```

Esse ambiente usa banco/volumes separados e a porta **4185**. Os testes criam dados fictícios próprios. Não aponte a variável de testes ao banco de uso real. As verificações e seus limites estão em [docs/VALIDACAO_ACADEMICA.md](docs/VALIDACAO_ACADEMICA.md).

## Edição anterior e dados existentes

A implementação PHP anterior e suas ferramentas permanecem em `static/`, `php/`, `database/` e `legacy/`. O README anterior está em `docs/EDICAO_PHP_ORIGINAL.md`; os `.bat` anteriores em `legacy/windows_php/` são apenas referência histórica (seus caminhos relativos pressupunham a raiz original).

A nova versão usa o banco separado **evofit_academico**. Ela não converte nem apaga um banco anterior. Para executar a edição PHP original, siga seu documento e use `python server.py --legacy-php` ou seu Compose original em outra porta, sem iniciar dois servidores na mesma porta.

## Documentação da entrega

| Documento | Conteúdo |
| --- | --- |
| [Relatório do projeto](docs/RELATORIO_PROJETO.md) | Problema, objetivos, desenvolvimento e resultados |
| [Requisitos e avaliação](docs/REQUISITOS_AVALIACAO.md) | Etapas e critérios definidos nos materiais das disciplinas |
| [Modelagem](docs/MODELAGEM.md) | Diagramas UML/ER/sequência, cardinalidades, dicionário e normalização |
| [Validação](docs/VALIDACAO_ACADEMICA.md) | Ambiente, procedimentos, resultados e limites dos testes |
| [Apresentação e sabatina](docs/ROTEIRO_APRESENTACAO.md) | Demonstração das funcionalidades e consultas SQL |

O documento **COMECE AQUI! (PROJETO)** estabelece as etapas de 09/11/2026 (UML e banco), 13/11/2026 (classes, DAOs e Flask) e 17/11/2026 (integração completa). A documentação apresenta as evidências técnicas correspondentes; os prazos não constituem registro de entrega nessas datas.

O código está disponível no repositório indicado no início deste documento. A orientação de entrega também exige adicionar o professor como colaborador pelo e-mail `leonardo.stephan@eaportal.org`; o estado desse convite deve ser conferido nas configurações do GitHub.

O servidor Flask utilizado é destinado a desenvolvimento e apresentação local.
