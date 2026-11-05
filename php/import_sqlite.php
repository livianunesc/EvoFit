<?php
declare(strict_types=1);
if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
require_once __DIR__ . '/bootstrap.php';
require_once __DIR__ . '/migration.php';
try {
    $input = stream_get_contents(STDIN, 100 * 1024 * 1024 + 1);
    if ($input === false || strlen($input) > 100 * 1024 * 1024) {
        throw new ApiError('Arquivo de migração ausente ou maior que 100 MB.', 400);
    }
    $payload = json_decode($input, true, 128, JSON_THROW_ON_ERROR);
    if (!is_array($payload) || array_is_list($payload)) {
        throw new ApiError('Arquivo de migração inválido.', 400);
    }
    // All validation happens before DDL or writes. DDL is intentionally outside the import transaction.
    $payload = evo_validate_import($payload);
    $db = evo_db();
    evo_schema($db);
    $counts = evo_import($db, $payload);
    fwrite(STDOUT, evo_json(['ok' => true, 'imported' => $counts]) . PHP_EOL);
} catch (ApiError $e) {
    fwrite(STDERR, $e->getMessage() . PHP_EOL);
    exit(1);
} catch (JsonException $e) {
    fwrite(STDERR, 'Arquivo de migração não contém JSON válido.' . PHP_EOL);
    exit(1);
} catch (Throwable $e) {
    fwrite(STDERR, 'Não foi possível importar. Confira a conexão e o esquema do MySQL; a importação de dados foi revertida.' . PHP_EOL);
    exit(1);
}
