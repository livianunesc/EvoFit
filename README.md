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

Os dois testes de integração usam banco temporário e verificam login, cadastro de aluno, criação e edição de treino, atribuição de dieta, registro de treino/cargas/medidas, atualização no personal, edição de perfil, persistência SQLite, logout, credenciais inválidas e isolamento entre usuários e personals. Testes de navegador também foram executados com Chromium: ambos os perfis, navegação, criação de treino, ausência de erros JavaScript e largura móvel de 390 px.

## Estrutura e persistência

- `server.py`: servidor HTTP, API, permissões, sessões e SQLite.
- `static/`: interface responsiva sem dependências externas.
- `tests/test_flow.py`: testes de integração.
- `evofit.sqlite3`: banco local, ignorado pelo Git. Contém dados pessoais: não publique esse arquivo.

Faça backup consistente do banco com a API SQLite (ou pare o servidor antes de copiar). O ZIP contém código e documentação, não os dados de usuários. Não exclua o banco para atualizar o código.

## Limitações de implantação

Esta entrega serve ao desenvolvimento e demonstração. O servidor HTTP da biblioteca padrão requer proxy HTTPS e endurecimento antes de exposição pública. Configure `SECURE_COOKIE=1` atrás de HTTPS; implemente limitação de tentativas de login, recuperação de senha, verificação de e-mail, política de dados e backups para produção. Sessões expiram em 24 horas; senhas usam scrypt com salt individual, cookies HttpOnly/SameSite e autorização no servidor. Não há envio de e-mails, sincronização automática, nem serviço de recuperação de senha. Planos alimentares devem ser orientados por profissional habilitado.

A autoria Git usa o nome e e-mail informados por Livia. Isso não constitui assinatura criptográfica de commits nem altera o titular da autenticação GitHub do ambiente.
