-- A conexão também precisa usar UTF-8 para preservar acentos nos clientes SQL.
SET NAMES utf8mb4;

-- EvoFit: consultas comentadas da rubrica BD AV2 (apostila 4º bimestre, p.30/38).
-- Execute schema.sql e o seed Python, depois dados_teste.sql no banco acadêmico.
-- Não usar no banco antigo. Toda consulta de equipe limita os dados ao personal.
-- Para estudar no cliente SQL, usamos variável de sessão com ID consultado por e-mail.
-- Na aplicação, o ID deve vir da sessão autenticada, como parâmetro do DAO (%s),
-- nunca de um campo confiado ao navegador. O e-mail abaixo é apenas demonstração.
SET @personal_id = (
    SELECT id FROM usuarios WHERE email = 'personal@evofit.demo' AND papel = 'personal'
);

-- 1. INNER JOIN: quais treinos pertencem aos alunos da equipe deste personal?
-- ON liga cada FK aluno_id à PK usuarios.id. Alunos sem treino ficam fora.
SELECT t.id AS treino_id, t.titulo, a.nome AS aluno
FROM treinos AS t
INNER JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id AND a.papel = 'aluno'
ORDER BY a.nome, a.id, t.id;

-- 2. LEFT JOIN: quantos treinos cada aluno possui, incluindo quem ainda não tem?
-- COUNT(t.id) conta apenas pares reais; COUNT(*) contaria também a linha com NULL.
-- O aluno iniciante do seed deve aparecer com total_treinos = 0.
SELECT a.id, a.nome, COUNT(t.id) AS total_treinos
FROM usuarios AS a
LEFT JOIN treinos AS t ON t.aluno_id = a.id
WHERE a.personal_id = @personal_id AND a.papel = 'aluno'
GROUP BY a.id, a.nome
ORDER BY a.nome, a.id;

-- 3. JOIN de QUATRO tabelas: qual é a ficha de exercícios de cada aluno da equipe?
-- A entidade associativa treino_exercicios resolve a relação N:N treino/exercício.
SELECT a.nome AS aluno, t.id AS treino_id, t.titulo, te.ordem,
       e.nome AS exercicio, e.grupo_muscular, te.series, te.repeticoes,
       te.carga, te.descanso
FROM usuarios AS a
INNER JOIN treinos AS t ON t.aluno_id = a.id
INNER JOIN treino_exercicios AS te ON te.treino_id = t.id
INNER JOIN exercicios AS e ON e.id = te.exercicio_id
WHERE a.personal_id = @personal_id AND a.papel = 'aluno'
ORDER BY a.id, t.id, te.ordem, te.id;

-- 4. LEFT JOIN sem correspondência: quais exercícios do catálogo não são prescritos?
-- O exercício de alongamento adicionado por dados_teste.sql deve aparecer.
-- O catálogo é compartilhado; este resultado não contém dados pessoais de equipes.
SELECT e.id, e.nome, e.grupo_muscular
FROM exercicios AS e
LEFT JOIN treino_exercicios AS te ON te.exercicio_id = e.id
WHERE te.id IS NULL
ORDER BY e.nome, e.id;

-- 5. Subquery escalar com AVG: quais conclusões superaram a carga média da equipe?
-- A consulta interna retorna UM número; AVG ignora NULL e retorna NULL sem linhas.
-- carga_total é soma das cargas informadas, em kg, não volume (séries x repetições).
SELECT r.id, a.nome AS aluno, t.titulo, r.carga_total
FROM registros AS r
JOIN treinos AS t ON t.id = r.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
  AND r.carga_total > (
      SELECT AVG(r2.carga_total)
      FROM registros AS r2
      JOIN treinos AS t2 ON t2.id = r2.treino_id
      JOIN usuarios AS a2 ON a2.id = t2.aluno_id
      WHERE a2.personal_id = @personal_id
  )
ORDER BY r.carga_total DESC, r.id;

-- 6. Subquery escalar com MAX: quais conclusões têm a maior carga da equipe?
-- Comparar com MAX mantém TODOS os empates, diferente de LIMIT 1.
SELECT r.id, a.nome, r.carga_total
FROM registros AS r
JOIN treinos AS t ON t.id = r.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
  AND r.carga_total = (
      SELECT MAX(r2.carga_total)
      FROM registros AS r2
      JOIN treinos AS t2 ON t2.id = r2.treino_id
      JOIN usuarios AS a2 ON a2.id = t2.aluno_id
      WHERE a2.personal_id = @personal_id
  )
ORDER BY r.id;

-- 7. Subquery escalar com MIN: quais conclusões têm a menor carga da equipe?
-- Uma carga menor não mede qualidade do treino; esta é uma consulta didática.
SELECT r.id, a.nome, r.carga_total
FROM registros AS r
JOIN treinos AS t ON t.id = r.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
  AND r.carga_total = (
      SELECT MIN(r2.carga_total)
      FROM registros AS r2
      JOIN treinos AS t2 ON t2.id = r2.treino_id
      JOIN usuarios AS a2 ON a2.id = t2.aluno_id
      WHERE a2.personal_id = @personal_id
  )
ORDER BY r.id;

-- 8. Subquery com IN: quais alunos da equipe já concluíram pelo menos um treino?
-- A subquery retorna um conjunto de IDs, e não um único valor.
SELECT a.id, a.nome
FROM usuarios AS a
WHERE a.personal_id = @personal_id AND a.papel = 'aluno'
  AND a.id IN (
      SELECT t.aluno_id FROM registros AS r JOIN treinos AS t ON t.id = r.treino_id
  )
ORDER BY a.nome, a.id;

-- 9. Subquery correlacionada EXISTS: quais treinos da equipe já têm histórico?
-- EXISTS só pergunta se existe um par; não duplica treino com várias conclusões.
SELECT t.id, t.titulo, a.nome AS aluno
FROM treinos AS t
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
  AND EXISTS (SELECT 1 FROM registros AS r WHERE r.treino_id = t.id)
ORDER BY t.id;

-- 10. NOT EXISTS: quais treinos da equipe ainda não foram concluídos?
-- Evita a armadilha de NOT IN quando a lista pode conter NULL.
-- O treino 'Mobilidade sem conclusão (avaliação)' deve aparecer antes de usá-lo.
SELECT t.id, t.titulo, a.nome AS aluno
FROM treinos AS t
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
  AND NOT EXISTS (SELECT 1 FROM registros AS r WHERE r.treino_id = t.id)
ORDER BY t.id;

-- 11. ORDER BY/LIMIT/OFFSET: primeira página do histórico da equipe, 2 por página.
-- Desempate por ID torna a ordem estável quando datas são iguais.
-- OFFSET = (pagina - 1) * tamanho: página 1 => 0; página 2 => 2; página 3 => 4.
SELECT r.id, a.nome AS aluno, t.titulo, r.concluido_em, r.carga_total
FROM registros AS r
JOIN treinos AS t ON t.id = r.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
ORDER BY r.concluido_em DESC, r.id DESC
LIMIT 2 OFFSET 0;

-- 12. Segunda página do mesmo histórico: usa os MESMOS filtros e ordenação.
-- Com seed + fixtures, as duas primeiras páginas contêm duas conclusões cada.
SELECT r.id, a.nome AS aluno, t.titulo, r.concluido_em, r.carga_total
FROM registros AS r
JOIN treinos AS t ON t.id = r.treino_id
JOIN usuarios AS a ON a.id = t.aluno_id
WHERE a.personal_id = @personal_id
ORDER BY r.concluido_em DESC, r.id DESC
LIMIT 2 OFFSET 2;

-- 13. Filtro no ON de LEFT JOIN: preservar alunos mesmo sem conclusão neste mês.
-- A conexão SQL deve usar UTC (+00:00); o mês desta consulta é um mês em UTC.
-- Não transferir r.concluido_em ao WHERE: isso eliminaria as linhas com NULL.
SELECT a.id, a.nome, COUNT(r.id) AS conclusoes_mes_utc
FROM usuarios AS a
LEFT JOIN treinos AS t ON t.aluno_id = a.id
LEFT JOIN registros AS r
       ON r.treino_id = t.id
      AND r.concluido_em >= DATE_FORMAT(UTC_TIMESTAMP(), '%Y-%m-01 00:00:00')
      AND r.concluido_em < DATE_FORMAT(UTC_TIMESTAMP() + INTERVAL 1 MONTH, '%Y-%m-01 00:00:00')
WHERE a.personal_id = @personal_id AND a.papel = 'aluno'
GROUP BY a.id, a.nome
ORDER BY conclusoes_mes_utc DESC, a.nome, a.id;

-- 14. Conferência: os treinos pertencem a alunos, e vínculos de equipe apontam
-- para personal? Deve retornar ZERO linhas. As FKs garantem existência da chave;
-- o papel do usuário relacionado é uma regra validada pelo serviço/DAO.
SELECT a.id, a.nome, a.papel, p.papel AS papel_do_responsavel
FROM usuarios AS a
LEFT JOIN usuarios AS p ON p.id = a.personal_id
WHERE (a.personal_id IS NOT NULL AND (a.papel <> 'aluno' OR p.papel <> 'personal'))
   OR (a.papel <> 'aluno' AND EXISTS (
       SELECT 1 FROM treinos AS t WHERE t.aluno_id = a.id
   ));
