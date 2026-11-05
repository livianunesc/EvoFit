# EvoFit

Plataforma fitness em português com personal e aluno, planos de treino e alimentação, cards interativos, cargas, medidas e histórico compartilhado. Autoria Git: **Livia Nunes Coelho**.

Esta versão usa **HTML, CSS, JavaScript, PHP, MySQL e Python**, com responsabilidades definidas:

| Tecnologia | Uso |
| --- | --- |
| HTML | Tela de login e estrutura da interface |
| CSS | Layout responsivo, cards e estilos |
| JavaScript | Navegação, formulários, gráficos e interação dos exercícios |
| PHP 8.2+ | API, autenticação, permissões e gravação dos dados |
| MySQL 8+ (ou MariaDB 10.4+) | Banco principal com transações e relacionamentos |
| Python 3.10+ | Inicialização, backup, migração do SQLite e validação inicial das senhas migradas |

O código Python/SQLite anterior está preservado em `legacy/server_sqlite.py`. O `server.py` da raiz agora inicia a versão **PHP/MySQL**.

## Abrir no Windows com XAMPP

1. Instale **XAMPP com PHP 8.2+** e **Python 3.10+**.
2. No painel do XAMPP, inicie **MySQL**. Para o servidor da porta 4173, Apache não é necessário.
3. Abra a pasta que contém `server.py` e execute **Preparar EvoFit.bat** na primeira vez.
4. Quando a preparação terminar, execute **Iniciar EvoFit.bat**.
5. O navegador abre o sistema na porta **4173**. Mantenha o terminal e o MySQL ligados.

Leia também **LEIA PRIMEIRO.txt**. Os scripts Windows foram revisados, mas a execução automatizada é validada em Linux; o passo a passo Windows depende da instalação local de XAMPP/Python.

O padrão local do XAMPP é `DB_HOST=127.0.0.1`, `DB_PORT=3306`, usuário `root` e senha vazia. Se sua instalação usa outros valores, copie `.env.example` para `.env` e ajuste. Preserve um `.env` já existente. Não use esses padrões de desenvolvimento em hospedagem pública.

## Instalação por terminal

Requisitos: PHP 8.2+ com PDO MySQL, MySQL 8+ e Python 3.10+. Não há Composer, npm ou pacotes Python obrigatórios. O PHP pode ser selecionado com `EVOFIT_PHP_BIN` ou com `--php CAMINHO` antes do subcomando de `tools/manage.py`; no Windows, `C:\xampp\php\php.exe` também é reconhecido.

Com o MySQL ligado e `.env` configurado:

```sh
# Apenas para um banco NOVO, sem dados a migrar:
python tools/manage.py init --create-database
python server.py
```

`--create-database` cria somente o nome configurado em `DB_NAME` e requer permissão do usuário MySQL. Sem essa opção, crie/selecione o banco previamente e execute `python tools/manage.py init`. O esquema é idempotente e as contas demo só são inseridas em banco vazio. Verificação: `python tools/manage.py check`.

Também é possível usar PHP diretamente:

```sh
php php/setup.php --create-database
php -S 127.0.0.1:4173 -t static router.php
```

`database/schema.sql` contém o esquema completo para importar no phpMyAdmin dentro do banco selecionado. Depois, `php php/setup.php` cria os dados de demonstração se o banco estiver vazio.

## Preservar os dados da versão antiga

Pare o servidor antigo, faça uma cópia de toda a pasta e preserve `evofit.sqlite3`. Configure **um MySQL vazio**, ainda sem executar o seed/demo:

```sh
python tools/manage.py migrate-sqlite evofit.sqlite3 --create-database
python server.py
```

A migração lê o SQLite sem alterar o original, cria backup consistente em `backups/` e importa usuários, vínculos, planos, registros e sessões de treino. Ela recusa um destino MySQL que já contenha dados. A importação é transacional; falhas mantêm os dados anteriores. Sessões de autenticação antigas não são transferidas: entre novamente. As senhas continuam válidas; no primeiro login, PHP chama o verificador Python por stdin e substitui o hash antigo por um hash nativo do PHP. As contas já convertidas não precisam desse verificador.

Não apague o SQLite ou seus backups depois de migrar. Eles não são incluídos no Git nem no ZIP. Os dados do MySQL ficam no serviço MySQL e exigem seus próprios backups. Parar a aplicação não apaga o banco.

## Demonstração

Em um banco inicializado do zero:

- **Personal:** `personal@evofit.demo`
- **Aluno:** `aluno@evofit.demo`
- **Senha de ambas:** `EvoFit123!`

As contas estão vinculadas e incluem treinos, refeições, medidas e histórico fictícios. Na migração, as contas existentes são mantidas, sem substituição por dados demo.

## Treinos e acompanhamento

O personal cadastra alunos, cria/edita divisões e atribui treinos e dietas ao aluno selecionado. Cada divisão aparece em um card. Ao abrir o card e expandir um exercício, o aluno vê ilustração, instruções, séries, repetições, descanso e controle de carga. **Concluir exercício** salva o progresso individual; recarregar a página permite retomar. **Ajustar carga** reabre o registro antes da finalização.

Quando todos os exercícios estiverem concluídos, **Concluir treino** registra o histórico e atualiza o painel do personal. Repetições da mesma finalização não duplicam o histórico. Alterações na prescrição invalidam somente o progresso ainda aberto; renomeações e imagens preservam as conclusões. O histórico completo permanece.

O aluno também consulta alimentação, registra medidas, acompanha gráficos e edita perfil. Atualize a página para ver alterações feitas em outra sessão. O cadastro livre de aluno cria uma conta independente; para acompanhamento, o personal cadastra o aluno com e-mail ainda não utilizado.

As imagens são diagramas SVG originais e funcionam sem internet. O personal escolhe uma ilustração no editor; exercícios sem referência específica usam a imagem genérica.

## Hospedagem e Apache

Configure o document root para **`static/`**, mantendo `php/`, `tools/`, `.env`, backups e SQL fora da área pública. A API está em `static/api.php`; o frontend usa caminhos relativos e funciona em subpastas. Em XAMPP/Apache, abrir `/EvoFit/static/` também funciona, mas evite expor os demais diretórios: configure um VirtualHost apontando para `static/` ou mantenha-os fora de `htdocs`. O arquivo `.htaccess` do projeto bloqueia o acesso direto ao código privado quando esse arranjo for usado.

Configure HTTPS, `SECURE_COOKIE=1` e um usuário MySQL restrito ao banco do aplicativo em produção. Servidores compartilhados podem desabilitar Python/proc_open; isso impede o primeiro login de uma conta migrada. Contas novas usam PHP diretamente. Não coloque credenciais reais no repositório.

## Docker opcional

Copie `.env.example` para `.env` e defina uma senha forte em `DOCKER_DB_PASSWORD`. MySQL usa volume persistente e não expõe sua porta externamente.

```sh
docker compose build
docker compose up -d db
# Banco novo:
docker compose run --rm app php php/setup.php
# Depois:
docker compose up -d app
```

Para migrar, faça a migração **antes de inicializar o demo**. Com o SQLite preservado na raiz, execute `docker compose run --rm -v "$PWD/evofit.sqlite3:/app/evofit.sqlite3:ro" -v "$PWD/backups:/app/backups" app python3 tools/manage.py migrate-sqlite /app/evofit.sqlite3`. O volume de backups deve ser gravável. Não use `docker compose down -v` se quiser preservar os dados.

## Validação

```sh
# Ferramentas Python (não requerem MySQL):
python -m unittest discover -s tests -p 'test_tools.py' -v
# Regressão da versão antiga, com SQLite temporário:
python -m unittest discover -s tests -p 'test_flow.py' -v
# Integração PHP em banco exclusivo de testes, nunca no banco de uso real:
EVOFIT_TEST_URL=http://127.0.0.1:4183 python tests/test_php_flow.py
# Interface PHP (requer Playwright e Chromium apenas para este teste):
EVOFIT_TEST_URL=http://127.0.0.1:4183 python tests/browser_php.py
```

Os resultados executados e os limites da validação estão em [docs/VALIDACAO.md](docs/VALIDACAO.md).

Os testes PHP criam contas e registros exclusivos de teste e não apagam o banco. Configure uma instância/banco separados antes de executá-los. Os exemplos com variáveis antes do comando usam sintaxe Bash; no PowerShell, defina `$env:EVOFIT_TEST_URL` antes de executar Python.

## Estrutura

- `static/`: HTML, CSS, JavaScript, ilustrações e entrada pública da API PHP.
- `php/`: configuração privada, API, autenticação, seed e importador.
- `database/schema.sql`: tabelas, chaves e índices MySQL.
- `tools/`: inicialização e migração em Python.
- `legacy/`: servidor Python/SQLite anterior, preservado para recuperação.
- `tests/`: testes das duas versões e das ferramentas.
- `.env.example`: configuração de exemplo sem segredos.

## Limitações

A entrega prepara desenvolvimento e demonstração. Antes de exposição pública, configure HTTPS, limitação de tentativas de login, recuperação/verificação de e-mail, política de dados e backups. Não há envio de e-mails nem atualização automática entre sessões. Planos alimentares devem ser orientados por profissional habilitado. A autoria Git não equivale a assinatura criptográfica do commit.
