# Arquitetura

O navegador carrega `static/index.html`, `style.css`, `app.js` e `workouts.js`. Os formulários chamam `api.php?route=...` com cookies de sessão. `php/api.php` valida os dados e o perfil antes de consultar ou alterar o MySQL por PDO/prepared statements. A API não devolve senhas ou hashes. As rotas `/api/...` são aliases do servidor de desenvolvimento.

`users.trainer` vincula cada aluno a um personal. `plans.student`, `logs.student` e `workout_runs.student` identificam o proprietário. `sessions` armazena somente o hash do token e a expiração. `workout_runs` mantém a prescrição original e cada carga/conclusão. A conclusão do treino ocorre dentro de transação e vincula um único registro em `logs`. Uma chave ativa gerada impede sessões abertas duplicadas para o mesmo aluno/plano.

Python é uma ferramenta operacional real: encontra o PHP/XAMPP, inicia o servidor e cria backup consistente antes de exportar o SQLite ao importador PHP. O importador exige destino vazio e valida relações antes de inserir. Os dados trafegam por stdin sem arquivos JSON contendo credenciais. As senhas antigas scrypt são verificadas por Python somente no primeiro login e atualizadas pelo PHP.

A versão antiga está em `legacy/server_sqlite.py`. Seu banco SQLite fica separado do MySQL; após migrar, use somente a versão nova para evitar históricos divergentes. O código original e as versões anteriores permanecem também no histórico Git.
