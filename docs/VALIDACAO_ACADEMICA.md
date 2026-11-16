# Relatório técnico de validação — EvoFit

**Autora:** Livia Nunes Coelho

**Data da validação:** 16/11/2026

A validação foi executada em Linux, com Python 3.12, Flask 3.1.2, MySQL 8.4, PHP 8.2/PDO MySQL e Chromium. Foram concluídos **27 testes automatizados**, dois fluxos de navegador e as 14 consultas SQL da avaliação de Banco de Dados, além das verificações de instalação, inicialização e integração PHP descritas abaixo.

A inicialização automática também foi verificada em uma suíte adicional de **8 testes**, descrita na seção específica abaixo.

Os resultados deste relatório correspondem à versão acadêmica com API Flask. Os relatórios anteriores documentam a edição PHP original, preservada no repositório.

| Verificação executada | Resultado |
| --- | --- |
| Build `Dockerfile.academico`, instalação das dependências | Passou; TLS/assinaturas mantidos |
| Inicialização principal e de testes, bancos separados | Passou; saúde do MySQL, schema, HTML e API verificados |
| Repetição da preparação no principal já inicializado | Passou; registros preservados e seed sem duplicação |
| `tests/test_academico.py` — entidades/POO | 2 testes passaram |
| `tests/test_academico.py` — integração MySQL real | 9 testes passaram, sem skips; suite completa de 11 em 30,049 s |
| `tests/test_tools.py` — ferramentas anteriores preservadas | 8 testes passaram |
| `tests/test_flow.py` — regressão Python/SQLite antiga | 8 testes passaram |
| Navegador principal `tests/browser_academico.py` | Passou: personal/aluno, CRUD completo, cargas/conclusão com versão, histórico/ranking, exclusões de fixtures, desktop/móvel 375 px e nenhum erro JavaScript |
| Navegador reduzido `tests/browser_apresentacao_academica.py` | Passou: login, conclusão real, histórico/ranking +1, persistência após reload, personal só consulta, logout e móvel sem overflow |
| PHP integrado `/relatorio-php` | Passou: login personal e relatório HTML com dados reais via PDO |
| Fontes locais e bloqueio de código/configuração privados | Passou: fonte TTF acessível; app.py, .env.academico, PHP privado e antiga entrada static/api.php retornam 404 |
| Sintaxe PHP, Python e JavaScript | Passou |
| `tests/test_inicializacao.py` — abertura automática do index | 8 testes passaram: prontidão HTTP, endereço correto, timeout e ausência de navegador |
| Inicializadores local e Docker com `--abrir` | Passaram em Linux com Flask/MySQL reais e chamada ao navegador capturada; abertura solicitada somente em `/index.html` |
| `banco/schema.sql`, `dados_teste.sql`, 14 consultas AV2 | Passaram em MySQL 8.4; fixture repetida não duplicou linhas; paginação mostrou duas páginas distintas |

## O que os testes demonstram

A integração usa conexões MySQL reais, sem substituir persistência por mocks. As fixtures possuem e-mails exclusivos. Os testes verificam SQL parametrizado, autenticação e cookie HttpOnly/SameSite, escopo de equipe, CRUD, rejeição de exclusões com vínculos, rollback após FK inválida, reenvio e finalizações concorrentes sem duplicação, HTTP 409 para ficha obsoleta e bloqueio de transferência de treino com histórico. Uma transferência sem histórico continua permitida.

As duas interfaces foram exercitadas no banco **evofit_academico_test**, separado do principal. A apresentação acrescenta conclusões à conta fictícia demo desse banco. A suíte principal cria suas próprias contas e remove somente fixtures explicitamente descartáveis; não apaga dados existentes de uso.

Os dados SQL de avaliação do principal são fictícios: após a preparação dos scripts houve 3 usuários, 6 exercícios, 3 treinos, 4 prescrições e 6 conclusões. Os totais mudam com o uso. As consultas demonstraram alunos/exercícios/treinos sem correspondência, AVG/MAX/MIN, IN/EXISTS, ordenação estável e duas páginas sem sobreposição. A auditoria de papéis não encontrou inconsistências.

## Reproduzir

```sh
python tools/docker_academico.py iniciar --testes
python tools/docker_academico.py validar --testes
```

Os testes de navegador são opcionais e executados fora do container, com Playwright e Chromium instalados:

```sh
python -m pip install playwright
python -m playwright install chromium
EVOFIT_TEST_URL=http://127.0.0.1:4185 EVOFIT_CONFIRMAR_BANCO_TESTE=1 python tests/browser_academico.py
EVOFIT_TEST_URL=http://127.0.0.1:4185 EVOFIT_CONFIRMAR_BANCO_TESTE=1 python tests/browser_apresentacao_academica.py
```

As atribuições antes do comando são sintaxe Bash; no PowerShell use `$env:EVOFIT_TEST_URL` e `$env:EVOFIT_CONFIRMAR_BANCO_TESTE`. `CHROMIUM_PATH` permite escolher um browser instalado. `EVOFIT_SCREENSHOT_DIR` escolhe a pasta de capturas, que por padrão é temporária. Capturas da validação estão em `docs/imagens/`.

## Inicialização automática da página principal

O inicializador abre `index.html` depois de confirmar o estado da API e a disponibilidade da página. A suíte usa um servidor HTTP local real e substitui somente o controlador do navegador. São verificados: espera pela saúde da API e pelo HTML, URL exata, respostas de erro, título incorreto, conexão recusada e navegador indisponível.

```sh
python -m unittest discover -s tests -p test_inicializacao.py -v
```

O fluxo `python server.py --abrir` foi exercitado com Flask e o banco de testes reais, em uma porta temporária. A chamada ao navegador foi capturada e conferida. Uma porta ocupada impediu o início e não abriu outro serviço. O fluxo Docker `iniciar --testes --abrir` também solicitou corretamente `/index.html` após as verificações. Os testes não abriram janelas reais de navegador do sistema operacional.

## Limites

- Os `.bat` foram preparados/revisados, mas não foram executados em Windows/XAMPP nativo nesta máquina.
- O schema prevê MariaDB 10.4+, mas a validação da versão acadêmica usou MySQL 8.4; a compatibilidade com MariaDB não foi verificada nesta execução.
- A interface é multipágina e o catálogo é compartilhado. Não há retomada parcial persistida nem snapshot histórico por exercício nesta versão acadêmica.
- As primeiras tentativas de navegador tiveram esperas de inicialização/transição insuficientes; as execuções finais aguardaram sessão e carregamento antes das verificações. Os testes finais passaram.
- A validação cobre execução local de desenvolvimento e apresentação. Não foi realizada implantação pública de produção.
