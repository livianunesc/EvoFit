# PHP complementar do EvoFit

**Autora do projeto:** Livia Nunes Coelho

O sistema avaliado usa **Python orientado a objetos, DAOs e Flask** como back-end principal.
Este módulo demonstra PHP 8, PDO, consulta MySQL parametrizada e geração de HTML,
integrado à mesma base normalizada `evofit_academico`.

O personal autenticado abre `/relatorio-php` pelo Flask. A rota confere o perfil na
sessão e inicia `php php_academico/relatorio.php`, enviando por stdin o objeto
`{"personal_id": ID_DA_SESSAO}`. O PHP consulta exclusivamente os alunos dessa equipe.
O usuário não escolhe o personal pela URL ou por um formulário.

O relatório não mostra e-mails, senhas ou hashes. Nomes vindos do banco passam por
`htmlspecialchars`, e os valores da consulta são associados com `PDO::prepare` e
`execute`, evitando tratar dados do usuário como SQL ou HTML executável.

## Execução e dependências

O runtime do Flask precisa de PHP 8 com a extensão `pdo_mysql`. O subprocesso recebe
`DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` e `DB_PASSWORD` no ambiente, com os mesmos
valores usados pelo DAO Python. Credenciais nunca devem ser incluídas no código.

O arquivo aceita somente PHP CLI. Não abra esse diretório pelo Apache nem inicie
um segundo servidor PHP para ele. A autenticação é feita uma única vez pelo Flask;
PHP não precisa conhecer a chave da sessão ou validar hashes Python novamente.

Contrato do processo:

- Entrada stdin: JSON com `personal_id` inteiro positivo, definido pelo servidor.
- Saída em sucesso: HTML UTF-8, status de saída `0`.
- Falha: mensagem genérica em stderr, status de saída `1`, sem detalhes de conexão.

## O que explicar na apresentação

1. Flask valida o login e restringe a rota ao personal.
2. PHP lê o identificador recebido por stdin e prepara a conexão PDO.
3. `LEFT JOIN` inclui alunos sem treinos e treinos sem conclusões.
4. `COUNT(DISTINCT ...)` conta treinos sem duplicá-los por registro de conclusão.
5. `COUNT`, `SUM`, `AVG` e `MAX` resumem os registros reais da equipe.
6. O HTML usa escape na saída, cabeçalhos de tabela e rolagem em telas pequenas.

`carga_total` significa a soma das cargas informadas em uma conclusão, **não volume
de treino**. Datas são armazenadas e exibidas neste relatório em UTC.
