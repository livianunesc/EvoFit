<?php
/**
 * EvoFit — relatório complementar em PHP 8 + PDO/MySQL.
 *
 * A aplicação principal continua sendo Python/Flask, como exige a avaliação.
 * Flask autentica o personal e entrega somente seu ID por stdin a este processo.
 * Não recebemos o ID da URL, não verificamos senhas novamente e não expomos
 * este arquivo em um servidor PHP: cada tecnologia tem uma responsabilidade.
 *
 * Entrada: {"personal_id": 123} em stdin. Saída: documento HTML completo.
 * Conexão: variáveis DB_HOST, DB_PORT, DB_NAME, DB_USER e DB_PASSWORD.
 */
declare(strict_types=1);

// CLI significa "linha de comando". A página pública é a rota Flask autenticada.
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}

/** Protege texto do banco antes de colocá-lo dentro do documento HTML. */
function escapar(mixed $valor): string
{
    return htmlspecialchars((string) $valor, ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
}

/** Formata números para a apresentação em português sem alterar o dado salvo. */
function numero(mixed $valor, int $casas = 0): string
{
    return number_format((float) $valor, $casas, ',', '.');
}

try {
    // A leitura limitada evita aceitar acidentalmente uma entrada muito grande.
    $entrada = stream_get_contents(STDIN, 4097);
    if ($entrada === false || strlen($entrada) > 4096) {
        throw new InvalidArgumentException('Entrada inválida.');
    }
    $dados = json_decode($entrada, true, 16, JSON_THROW_ON_ERROR);
    $personalId = is_array($dados) ? ($dados['personal_id'] ?? null) : null;
    if (!is_int($personalId) || $personalId < 1) {
        throw new InvalidArgumentException('Identificador inválido.');
    }

    // Valores secretos são lidos do ambiente e nunca aparecem no HTML/log.
    $host = getenv('DB_HOST') ?: '127.0.0.1';
    $porta = getenv('DB_PORT') ?: '3306';
    $banco = getenv('DB_NAME') ?: 'evofit_academico';
    $usuario = getenv('DB_USER') ?: 'evofit';
    $senha = getenv('DB_PASSWORD');
    if (!preg_match('/^[A-Za-z0-9_]+$/D', $banco)
        || !ctype_digit($porta) || (int) $porta < 1 || (int) $porta > 65535
        || preg_match('/[;\x00-\x20]/', $host)) {
        throw new InvalidArgumentException('Configuração inválida.');
    }
    $pdo = new PDO(
        "mysql:host={$host};port={$porta};dbname={$banco};charset=utf8mb4",
        $usuario,
        $senha === false ? '' : $senha,
        [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
         PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
         PDO::ATTR_EMULATE_PREPARES => false]
    );

    // PDO prepara a instrução; o ID vira um parâmetro, nunca parte do SQL.
    $consulta = $pdo->prepare(
        "SELECT id, nome FROM usuarios WHERE id = :id AND papel = 'personal'"
    );
    $consulta->execute(['id' => $personalId]);
    $personal = $consulta->fetch();
    if (!$personal) {
        throw new InvalidArgumentException('Personal não encontrado.');
    }

    /*
     * LEFT JOIN mantém alunos sem treinos e treinos sem registros no relatório.
     * COUNT(DISTINCT treino.id) evita contar o mesmo treino a cada conclusão.
     * A condição personal_id restringe todas as linhas à equipe autenticada.
     * O desempate pelo ID deixa a ordenação estável entre nomes iguais.
     */
    $consulta = $pdo->prepare(<<<'SQL'
        SELECT aluno.id, aluno.nome,
               COUNT(DISTINCT treino.id) AS treinos,
               COUNT(registro.id) AS conclusoes,
               COALESCE(SUM(registro.carga_total), 0) AS carga_acumulada,
               COALESCE(AVG(registro.carga_total), 0) AS media_carga,
               MAX(registro.concluido_em) AS ultima_conclusao
          FROM usuarios AS aluno
          LEFT JOIN treinos AS treino ON treino.aluno_id = aluno.id
          LEFT JOIN registros AS registro ON registro.treino_id = treino.id
         WHERE aluno.personal_id = :personal_id AND aluno.papel = 'aluno'
         GROUP BY aluno.id, aluno.nome
         ORDER BY conclusoes DESC, aluno.id ASC
        SQL);
    $consulta->execute(['personal_id' => $personalId]);
    $alunos = $consulta->fetchAll();
} catch (Throwable $erro) {
    // O servidor pode traduzir esse erro; detalhes da conexão não são públicos.
    fwrite(STDERR, "Não foi possível gerar o relatório PHP. Verifique o banco e a configuração.\n");
    exit(1);
}
?>
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Relatório da equipe | EvoFit</title>
    <style>
        * { box-sizing: border-box; }
        body { margin: 0; background: #f4f6ef; color: #172015; font: 1rem/1.6 system-ui, sans-serif; }
        main { width: min(1100px, 94%); margin: 2rem auto; }
        header { padding: 1.5rem; border-radius: 1rem; background: #192318; color: white; }
        h1 { margin: .2rem 0; font-size: clamp(1.6rem, 5vw, 2.6rem); }
        .marca { color: #c7f34b; font-weight: 800; letter-spacing: .12em; }
        .voltar { display: inline-block; margin: 1rem 0; color: #264e0b; font-weight: 700; }
        .tabela { overflow-x: auto; background: white; border-radius: .8rem; border: 1px solid #dae0d1; }
        table { width: 100%; border-collapse: collapse; }
        caption { text-align: left; padding: 1rem; font-weight: 700; }
        th, td { padding: .8rem 1rem; border-top: 1px solid #e2e7dc; text-align: left; }
        thead { background: #e7efda; }
        tbody th { font-weight: 600; }
        .nota { padding: 1rem; background: #e7efda; border-radius: .8rem; }
        a:focus-visible { outline: 3px solid #548d17; outline-offset: 3px; }
        @media print { body { background: white; } .voltar { display: none; } main { width: 100%; margin: 0; } }
    </style>
</head>
<body>
<main>
    <header>
        <span class="marca">EVOFIT</span>
        <h1>Relatório da equipe</h1>
        <p>Personal: <?= escapar($personal['nome']) ?></p>
    </header>
    <a class="voltar" href="/pages/relatorios.html">← Voltar aos relatórios</a>
    <section aria-labelledby="titulo-tabela">
        <h2 id="titulo-tabela">Acompanhamento dos alunos</h2>
        <div class="tabela" role="region" aria-label="Resumo da equipe, tabela com rolagem horizontal" tabindex="0">
            <table>
                <caption>Somente alunos vinculados ao personal autenticado</caption>
                <thead><tr>
                    <th scope="col">Aluno</th><th scope="col">Treinos cadastrados</th>
                    <th scope="col">Conclusões</th><th scope="col">Cargas acumuladas (kg)</th>
                    <th scope="col">Média por conclusão (kg)</th><th scope="col">Última conclusão (UTC)</th>
                </tr></thead>
                <tbody>
                <?php if (!$alunos): ?>
                    <tr><td colspan="6">Nenhum aluno cadastrado nesta equipe.</td></tr>
                <?php else: ?>
                    <?php foreach ($alunos as $aluno): ?>
                    <tr>
                        <th scope="row"><?= escapar($aluno['nome']) ?></th>
                        <td><?= numero($aluno['treinos']) ?></td>
                        <td><?= numero($aluno['conclusoes']) ?></td>
                        <td><?= numero($aluno['carga_acumulada'], 2) ?></td>
                        <td><?= numero($aluno['media_carga'], 2) ?></td>
                        <td><?= escapar($aluno['ultima_conclusao'] ?? 'Sem conclusões') ?></td>
                    </tr>
                    <?php endforeach; ?>
                <?php endif; ?>
                </tbody>
            </table>
        </div>
    </section>
    <p class="nota">A carga de uma conclusão é a soma das cargas informadas nos exercícios.
        Essa soma não representa volume de treino (séries × repetições × carga).
        Datas do banco são mostradas em UTC. Alunos sem treinos ou sem conclusões também aparecem.</p>
    <footer><p>Consulta SQL com PDO, parâmetros, LEFT JOIN, COUNT, SUM, AVG e MAX.
        A autenticação e as rotas do sistema são responsabilidade do Python/Flask.</p></footer>
</main>
</body>
</html>
