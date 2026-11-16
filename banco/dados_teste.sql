-- A conexão também precisa usar UTF-8 para preservar acentos nos clientes SQL.
SET NAMES utf8mb4;

-- Dados complementares de avaliação. Execute primeiro: python app.py init-db
-- O seed Python cria as contas demo usando hashes reais, sem senha em SQL.
-- Selecione o MESMO banco acadêmico da aplicação antes de importar este arquivo.
-- Pode repetir: os INSERT ... SELECT ... WHERE NOT EXISTS não duplicam os casos.
-- Dados fictícios; não use este script no banco da instalação antiga.

-- A ausência de linhas aqui indica que o seed Python ainda não foi executado.
SELECT id, nome, papel
FROM usuarios
WHERE email IN ('personal@evofit.demo', 'aluno@evofit.demo')
ORDER BY papel, id;

-- Catálogo sem prescrição: o LEFT JOIN deve preservar o exercício com treino NULL.
INSERT INTO exercicios (nome, grupo_muscular, instrucoes)
SELECT 'Alongamento de panturrilha (avaliação)', 'Mobilidade',
       'Apoie as mãos na parede e alongue sem dor. Exemplo fictício para a avaliação.'
WHERE NOT EXISTS (
    SELECT 1 FROM exercicios WHERE nome = 'Alongamento de panturrilha (avaliação)'
);

-- Um treino ainda não concluído é um caso sem correspondência em registros.
-- Não cria usuários nem altera a senha das contas demonstrativas.
INSERT INTO treinos (aluno_id, titulo)
SELECT u.id, 'Mobilidade sem conclusão (avaliação)'
FROM usuarios AS u
WHERE u.email = 'aluno@evofit.demo' AND u.papel = 'aluno'
  AND NOT EXISTS (
      SELECT 1 FROM treinos AS t
      WHERE t.aluno_id = u.id AND t.titulo = 'Mobilidade sem conclusão (avaliação)'
  );

-- Associa o treino a um OUTRO exercício para manter o primeiro sem prescrição.
INSERT INTO exercicios (nome, grupo_muscular, instrucoes)
SELECT 'Mobilidade de ombros (avaliação)', 'Mobilidade',
       'Faça movimentos leves e controlados, respeitando sua amplitude.'
WHERE NOT EXISTS (
    SELECT 1 FROM exercicios WHERE nome = 'Mobilidade de ombros (avaliação)'
);

INSERT INTO treino_exercicios
    (treino_id, exercicio_id, ordem, series, repeticoes, carga, descanso)
SELECT t.id, e.id, 0, 2, '10', 0, 30
FROM treinos AS t
JOIN usuarios AS u ON u.id = t.aluno_id
JOIN exercicios AS e ON e.id = (
    SELECT MIN(e2.id) FROM exercicios AS e2
    WHERE e2.nome = 'Mobilidade de ombros (avaliação)'
)
WHERE u.email = 'aluno@evofit.demo'
  AND t.titulo = 'Mobilidade sem conclusão (avaliação)'
  AND NOT EXISTS (
      SELECT 1 FROM treino_exercicios AS te WHERE te.treino_id = t.id AND te.ordem = 0
  );

-- Histórico adicional FICTÍCIO para demonstrar duas páginas com dados reais no banco.
-- Estes eventos não vieram de pessoas treinando: são fixtures da avaliação.
-- O treino é derivado da conclusão criada pelo seed Python, sem assumir IDs fixos.
-- A chave única identifica cada fixture e impede inserção duplicada nas repetições.
INSERT INTO registros (treino_id, concluido_em, carga_total, chave)
SELECT base.treino_id, UTC_TIMESTAMP() - INTERVAL f.dias DAY,
       f.carga, CONCAT('fixture-avaliacao-', f.numero)
FROM registros AS base
JOIN treinos AS t ON t.id = base.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
CROSS JOIN (
    SELECT 1 AS numero, 4 AS dias, 32.00 AS carga
    UNION ALL SELECT 2, 3, 34.00
    UNION ALL SELECT 3, 2, 36.00
    UNION ALL SELECT 4, 1, 38.00
) AS f
WHERE base.chave = 'seed-demo-1' AND a.email = 'aluno@evofit.demo'
  AND NOT EXISTS (
      SELECT 1 FROM registros AS anterior
      WHERE anterior.chave = CONCAT('fixture-avaliacao-', f.numero)
  );

-- Verifique o efeito: deve existir pelo menos um exercício sem prescrição e um
-- treino sem conclusão. Totais não são fixos: o uso da aplicação acrescenta dados.
SELECT 'exercicios_sem_treino' AS caso, COUNT(*) AS total
FROM exercicios AS e
WHERE NOT EXISTS (SELECT 1 FROM treino_exercicios AS te WHERE te.exercicio_id = e.id)
UNION ALL
SELECT 'treinos_sem_conclusao', COUNT(*)
FROM treinos AS t
WHERE NOT EXISTS (SELECT 1 FROM registros AS r WHERE r.treino_id = t.id);
