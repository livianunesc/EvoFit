# Validação da conversão PHP/MySQL

Executada em ambiente Linux em 5 de novembro de 2026.

| Verificação | Resultado |
| --- | --- |
| API com PHP 8.3.36 e MySQL 8.4 | 8 testes passaram |
| Mesma API com MariaDB 10.4.34 (compatibilidade com XAMPP) | 8 testes passaram |
| Ferramentas Python de backup, migração e senha legada | 8 testes passaram |
| Regressão da versão Python/SQLite preservada | 8 testes passaram |
| Migração integrada para MySQL vazio | 1 cenário completo passou |
| Navegador Chromium com PHP/MySQL | Fluxo completo passou |
| Frontend instalado em subpasta | Login, cookie, cards e imagens passaram |
| Dockerfile, Compose e preparação repetida | Build e inicialização passaram |
| Sintaxe PHP e JavaScript | Sem erros |

A API foi testada com contas isoladas: cadastro, personal/aluno, dieta, treino, cargas, conclusão parcial, retomada, finalização simultânea sem duplicação, medidas, perfil, logout, versões desatualizadas, repetições inválidas e acesso negado entre usuários. O teste de navegador verificou também escape de HTML armazenado, imagens, edição pelo personal, foco e layout móvel de 390 px.

O teste de migração usa origem SQLite temporária, destino MySQL vazio e dados com sessões de treino ativas, concluídas e invalidadas. Confere IDs, vínculos, textos JSON, hashes e datas; origem intacta e backup consistente; rejeição de relacionamentos inválidos; rollback de uma falha SQL real; recusa de reimportação; ausência de sessões antigas de login; atualização de senha e conclusão de um treino retomado. Para repeti-lo, prepare outro MySQL vazio e forneça `EVOFIT_MIGRATION_PHP` (executável/wrapper PHP que seleciona esse banco) e `EVOFIT_MIGRATION_URL`, depois execute `python tests/test_php_migration.py`. O script recusa um alvo preenchido.

Também foi migrado o banco SQLite já existente nesta instância: 2 usuários, 3 planos e 4 registros de histórico. A comparação conferiu os dados antes do primeiro login; ambos os logins funcionaram e atualizaram seus hashes. Uma segunda importação foi recusada sem alterar o destino ou o SQLite.

A aplicação final foi iniciada na porta 4173 usando Compose. A publicação de um ambiente e a execução em nova máquina são etapas separadas. Os arquivos `.bat` foram revisados; não houve execução em Windows nem no aplicativo XAMPP gráfico. MariaDB foi validado em container Linux. Não foi feita implantação pública de produção.

## Interface Focus e ranking — 6 de novembro de 2026

A nova interface é focada em treino e foi verificada com PHP/MySQL reais em banco exclusivo de testes. Os 8 testes existentes de API continuaram passando. Foram acrescentadas 6 verificações de ranking: isolamento entre equipes, privacidade dos campos, empates, treino parcial sem pontuação, finalização idempotente, mês/geral, vínculos independentes, limites mensais UTC/fuso, datas antigas sem horário e horário de verão.

O teste Chromium foi atualizado para a navegação Painel/Treinos/Ranking/Histórico e gestão de atletas pelo personal. Usa contas fictícias criadas pela API, com quatro divisões de treino e registros reais de conclusão: os gráficos e os números são comparados com esses registros. Verificou carrossel, setas, indicadores, teclado, exercícios, imagens, carga, retomada, finalização, histórico, ranking, filtros e edição. Dieta e perfil não aparecem na navegação.

A versão móvel de 375 px foi conferida sem overflow horizontal, com botão de treino totalmente dentro do hero e preferência de movimento reduzido respeitada. Fontes e fotografia carregam localmente. A revisão também protegeu a interface contra respostas antigas de requisições após logout ou troca de conta. A migração e os dados antigos não sofreram alteração destrutiva.

O teste opcional de navegador da versão SQLite preservada também foi adaptado e passou com banco temporário. O ranking principal pertence à versão PHP/MySQL. Os scripts Windows continuam sem execução nativa nesta máquina Linux.

As 6 verificações do ranking também passaram no MariaDB 10.4.34, sem skips. As regressões de autenticação foram executadas no Chromium: uma resposta real atrasada após logout não reabre o painel; após entrar em outra conta, a resposta antiga não substitui o nome, a equipe ou os dados atuais. O tratamento de datas sem horário foi conferido com UTC e conversão para São Paulo.
