<?php
declare(strict_types=1);

/** Validate a legacy export entirely before touching the target database. */
function evo_migration_fail(string $message): never
{
    throw new ApiError('Migração recusada: ' . $message, 400);
}

function evo_migration_id(mixed $value, string $field): int
{
    if (!is_int($value) || $value < 1) {
        evo_migration_fail('identificador inválido em ' . $field . '.');
    }
    return $value;
}

function evo_migration_text(mixed $value, string $field, int $max = 1000000, bool $empty = true): string
{
    if (!is_string($value) || strlen($value) > $max || (!$empty && trim($value) === '')) {
        evo_migration_fail('texto inválido em ' . $field . '.');
    }
    return $value;
}

function evo_migration_number(mixed $value, string $field, float $min = 0): float
{
    if (is_bool($value) || (!is_int($value) && !is_float($value) && !is_string($value)) || !is_numeric($value)) {
        evo_migration_fail('número inválido em ' . $field . '.');
    }
    $number = (float) $value;
    if (!is_finite($number) || $number < $min) {
        evo_migration_fail('número inválido em ' . $field . '.');
    }
    return $number;
}

function evo_migration_json(mixed $value, string $field, bool $list): array
{
    if (is_string($value)) {
        try {
            $value = json_decode($value, true, 128, JSON_THROW_ON_ERROR);
        } catch (JsonException $e) {
            evo_migration_fail('JSON inválido em ' . $field . '.');
        }
    }
    if (!is_array($value) || ($list && !array_is_list($value)) || (!$list && $value !== [] && array_is_list($value))) {
        evo_migration_fail('estrutura inválida em ' . $field . '.');
    }
    return $value;
}

function evo_migration_date(mixed $value, string $field): string
{
    $date = evo_migration_text($value, $field, 32, false);
    $format = strlen($date) === 10 ? '!Y-m-d' : '!Y-m-d H:i:s';
    $parsed = DateTimeImmutable::createFromFormat($format, $date, new DateTimeZone('UTC'));
    $errors = DateTimeImmutable::getLastErrors();
    if (!$parsed || ($errors !== false && ($errors['warning_count'] || $errors['error_count'])) || $parsed->format(strlen($date) === 10 ? 'Y-m-d' : 'Y-m-d H:i:s') !== $date) {
        evo_migration_fail('data inválida em ' . $field . '.');
    }
    return $date;
}

function evo_migration_workout(array $items): array
{
    if (!$items) {
        evo_migration_fail('treino sem exercícios.');
    }
    $snapshot = [];
    foreach ($items as $item) {
        if (!is_array($item) || array_is_list($item)) {
            evo_migration_fail('exercício inválido.');
        }
        $name = evo_migration_text($item['name'] ?? null, 'nome do exercício', 1000, false);
        $reps = $item['reps'] ?? null;
        if ((!is_string($reps) && !is_int($reps) && !is_float($reps)) || trim((string) $reps) === '') {
            evo_migration_fail('repetições inválidas.');
        }
        $sets = evo_migration_number($item['sets'] ?? null, 'séries');
        if ($sets <= 0) {
            evo_migration_fail('séries inválidas.');
        }
        $snapshot[] = [
            'name' => trim($name), 'reps' => trim((string) $reps),
            'notes' => trim(evo_migration_text($item['notes'] ?? '', 'observações')),
            'sets' => $sets, 'load' => evo_migration_number($item['load'] ?? null, 'carga'),
            'rest' => evo_migration_number($item['rest'] ?? null, 'descanso'),
        ];
    }
    return $snapshot;
}

function evo_validate_import(array $export): array
{
    if (($export['format'] ?? null) !== 'evofit-sqlite' || ($export['version'] ?? null) !== 1) {
        evo_migration_fail('formato ou versão do arquivo não suportados.');
    }
    foreach (array_keys($export) as $key) {
        if (!in_array($key, ['format', 'version', 'users', 'plans', 'logs', 'workout_runs'], true)) {
            evo_migration_fail('campo desconhecido no arquivo de exportação.');
        }
    }
    foreach (['users', 'plans', 'logs', 'workout_runs'] as $table) {
        $rows = $export[$table] ?? ($table === 'workout_runs' ? [] : null);
        if (!is_array($rows) || !array_is_list($rows)) {
            evo_migration_fail('lista de ' . $table . ' inválida.');
        }
        $export[$table] = $rows;
    }
    $users = []; $emails = [];
    foreach ($export['users'] as &$user) {
        if (!is_array($user)) {
            evo_migration_fail('usuário inválido.');
        }
        $id = evo_migration_id($user['id'] ?? null, 'usuário');
        if (isset($users[$id])) {
            evo_migration_fail('identificador de usuário repetido.');
        }
        evo_migration_text($user['name'] ?? null, 'nome', 1000000, false);
        $email = evo_migration_text($user['email'] ?? null, 'e-mail', 200, false);
        if (!str_contains($email, '@') || isset($emails[strtolower($email)])) {
            evo_migration_fail('e-mail inválido ou repetido.');
        }
        $emails[strtolower($email)] = true;
        if (!in_array($user['role'] ?? null, ['personal', 'aluno'], true)) {
            evo_migration_fail('perfil de usuário inválido.');
        }
        $hash = evo_migration_text($user['password'] ?? null, 'hash da senha', 255, false);
        $nativeHash = str_starts_with($hash, 'sha256:') ? substr($hash, 7) : $hash;
        if (!preg_match('/\A[0-9a-f]{32}:[0-9a-f]{128}\z/i', $hash) && (password_get_info($nativeHash)['algoName'] ?? 'unknown') === 'unknown') {
            evo_migration_fail('formato de senha armazenada não suportado.');
        }
        $user['trainer'] = $user['trainer'] ?? null;
        if ($user['trainer'] !== null) {
            evo_migration_id($user['trainer'], 'vínculo do personal');
        }
        $user['goal'] = $user['goal'] ?? '';
        evo_migration_text($user['goal'], 'objetivo');
        $users[$id] = $user;
    }
    unset($user);
    foreach ($users as $user) {
        if ($user['trainer'] !== null && ($user['role'] !== 'aluno' || !isset($users[$user['trainer']]) || $users[$user['trainer']]['role'] !== 'personal')) {
            evo_migration_fail('vínculo entre aluno e personal inválido.');
        }
    }
    $plans = [];
    foreach ($export['plans'] as &$plan) {
        if (!is_array($plan)) {
            evo_migration_fail('plano inválido.');
        }
        $id = evo_migration_id($plan['id'] ?? null, 'plano');
        $sid = evo_migration_id($plan['student'] ?? null, 'aluno do plano');
        if (isset($plans[$id]) || !isset($users[$sid]) || $users[$sid]['role'] !== 'aluno') {
            evo_migration_fail('identificador de plano repetido ou aluno inválido.');
        }
        evo_migration_text($plan['title'] ?? null, 'título', 1000000, false);
        if (!in_array($plan['kind'] ?? null, ['workout', 'diet'], true)) {
            evo_migration_fail('tipo de plano inválido.');
        }
        $items = evo_migration_json($plan['items'] ?? null, 'itens do plano', true);
        if (!$items) {
            evo_migration_fail('plano sem itens.');
        }
        if ($plan['kind'] === 'workout') {
            evo_migration_workout($items);
        } else {
            foreach ($items as $item) {
                if (!is_array($item)) {
                    evo_migration_fail('refeição inválida.');
                }
                foreach (['name', 'time', 'food', 'quantity'] as $field) {
                    evo_migration_text($item[$field] ?? null, 'refeição/' . $field, 1000000, false);
                }
            }
        }
        // Preserve the original JSON text when available, rather than rewriting user data.
        $plan['_items'] = $items;
        $plans[$id] = $plan;
    }
    unset($plan);
    $logs = [];
    foreach ($export['logs'] as &$log) {
        if (!is_array($log)) {
            evo_migration_fail('histórico inválido.');
        }
        $id = evo_migration_id($log['id'] ?? null, 'histórico');
        $sid = evo_migration_id($log['student'] ?? null, 'aluno do histórico');
        if (isset($logs[$id]) || !isset($users[$sid]) || $users[$sid]['role'] !== 'aluno') {
            evo_migration_fail('identificador de histórico repetido ou aluno inválido.');
        }
        if (!in_array($log['kind'] ?? null, ['workout', 'measurement'], true)) {
            evo_migration_fail('tipo de histórico inválido.');
        }
        $data = evo_migration_json($log['data'] ?? null, 'dados do histórico', false);
        if ($log['kind'] === 'measurement') {
            foreach (['weight', 'waist', 'hip', 'chest'] as $field) {
                $n = evo_migration_number($data[$field] ?? null, $field);
                if ($n <= 0 || $n >= 500) {
                    evo_migration_fail('medida fora do intervalo permitido.');
                }
            }
        } else {
            evo_migration_text($data['title'] ?? null, 'título do histórico', 1000000, false);
            $exercises = evo_migration_json($data['exercises'] ?? null, 'exercícios do histórico', true);
            foreach ($exercises as $exercise) {
                if (!is_array($exercise)) {
                    evo_migration_fail('exercício no histórico inválido.');
                }
                evo_migration_text($exercise['name'] ?? null, 'nome do exercício no histórico', 1000, false);
                evo_migration_number($exercise['load'] ?? null, 'carga no histórico');
                if (isset($exercise['done']) && !is_bool($exercise['done'])) {
                    evo_migration_fail('conclusão no histórico inválida.');
                }
            }
        }
        $log['date'] = evo_migration_date($log['date'] ?? null, 'data do histórico');
        $logs[$id] = $log;
    }
    unset($log);
    $sessions = []; $active = [];
    foreach ($export['workout_runs'] as &$run) {
        if (!is_array($run)) {
            evo_migration_fail('sessão de treino inválida.');
        }
        $session = evo_migration_text($run['session'] ?? null, 'sessão de treino', 100, false);
        if (!preg_match('/\A[A-Za-z0-9_-]{1,100}\z/', $session)) {
            evo_migration_fail('identificador de sessão de treino inválido.');
        }
        if (isset($sessions[$session])) {
            evo_migration_fail('sessão de treino repetida.');
        }
        $sessions[$session] = true;
        $sid = evo_migration_id($run['student'] ?? null, 'aluno da sessão');
        $pid = evo_migration_id($run['plan'] ?? null, 'treino da sessão');
        if (!isset($users[$sid]) || !isset($plans[$pid]) || $users[$sid]['role'] !== 'aluno' || $plans[$pid]['student'] !== $sid || $plans[$pid]['kind'] !== 'workout') {
            evo_migration_fail('vínculo de sessão de treino inválido.');
        }
        if (!in_array($run['status'] ?? null, ['active', 'completed', 'invalidated'], true)) {
            evo_migration_fail('estado da sessão inválido.');
        }
        $snapshot = evo_migration_json($run['snapshot'] ?? null, 'prescrição da sessão', true);
        $canonical = evo_migration_workout($snapshot);
        $exercises = evo_migration_json($run['exercises'] ?? null, 'exercícios da sessão', true);
        if (count($snapshot) !== count($exercises)) {
            evo_migration_fail('quantidade de exercícios da sessão inconsistente.');
        }
        foreach ($exercises as $exercise) {
            if (!is_array($exercise) || !is_bool($exercise['done'] ?? null)) {
                evo_migration_fail('conclusão da sessão inválida.');
            }
            $n = evo_migration_number($exercise['load'] ?? null, 'carga da sessão');
            if ($n >= 2000) {
                evo_migration_fail('carga da sessão fora do intervalo permitido.');
            }
            if ($run['status'] === 'completed' && !$exercise['done']) {
                evo_migration_fail('sessão finalizada com exercícios pendentes.');
            }
        }
        $run['log'] = $run['log'] ?? null;
        if ($run['status'] === 'completed') {
            $logId = evo_migration_id($run['log'], 'histórico da sessão');
            if (!isset($logs[$logId]) || $logs[$logId]['student'] !== $sid || $logs[$logId]['kind'] !== 'workout') {
                evo_migration_fail('histórico da sessão não encontrado.');
            }
        } elseif ($run['log'] !== null) {
            evo_migration_fail('sessão pendente vinculada a histórico finalizado.');
        }
        if ($run['status'] === 'active') {
            $key = $sid . ':' . $pid;
            if (isset($active[$key]) || $canonical != evo_migration_workout($plans[$pid]['_items'])) {
                evo_migration_fail('progresso ativo duplicado ou incompatível com o plano.');
            }
            $active[$key] = true;
        }
        $run['updated'] = evo_migration_date($run['updated'] ?? null, 'data da sessão');
    }
    unset($run);
    return $export;
}

/** Import into an empty target atomically; never delete existing records or copy auth sessions. */
function evo_import(PDO $db, array $export): array
{
    if ($db->inTransaction()) {
        throw new ApiError('A migração precisa de uma conexão fora de transação.', 409);
    }
    $data = evo_validate_import($export);
    $lockName = 'evofit-maintenance-' . substr(hash('sha256', getenv('DB_NAME') ?: 'evofit'), 0, 40);
    $lock = $db->prepare('SELECT GET_LOCK(?, 10)');
    $lock->execute([$lockName]);
    if ((int) $lock->fetchColumn() !== 1) {
        throw new ApiError('Outra preparação do banco está em andamento. Aguarde e tente novamente.', 409);
    }
    try {
        $db->exec('SET TRANSACTION ISOLATION LEVEL SERIALIZABLE');
        $db->beginTransaction();
        // Gap locks prevent concurrent first registrations from racing the empty-target check.
        foreach (['users' => 'id', 'plans' => 'id', 'logs' => 'id', 'workout_runs' => 'session', 'sessions' => 'token'] as $table => $key) {
            if ($db->query('SELECT `' . $key . '` FROM `' . $table . '` LIMIT 1 FOR UPDATE')->fetchColumn() !== false) {
                throw new ApiError('O banco MySQL já contém dados. Use um banco vazio; nenhum registro foi substituído.', 409);
            }
        }
        $insert = $db->prepare('INSERT INTO users(id,name,email,password,role,trainer,goal) VALUES(?,?,?,?,?,NULL,?)');
        foreach ($data['users'] as $row) {
            $insert->execute([$row['id'], $row['name'], $row['email'], $row['password'], $row['role'], $row['goal']]);
        }
        $link = $db->prepare('UPDATE users SET trainer=? WHERE id=?');
        foreach ($data['users'] as $row) {
            if ($row['trainer'] !== null) {
                $link->execute([$row['trainer'], $row['id']]);
            }
        }
        $insert = $db->prepare('INSERT INTO plans(id,student,kind,title,items) VALUES(?,?,?,?,?)');
        foreach ($data['plans'] as $row) {
            $insert->execute([$row['id'], $row['student'], $row['kind'], $row['title'], is_string($row['items']) ? $row['items'] : evo_json($row['items'])]);
        }
        $insert = $db->prepare('INSERT INTO logs(id,student,kind,data,date) VALUES(?,?,?,?,?)');
        foreach ($data['logs'] as $row) {
            $insert->execute([$row['id'], $row['student'], $row['kind'], is_string($row['data']) ? $row['data'] : evo_json($row['data']), $row['date']]);
        }
        $insert = $db->prepare('INSERT INTO workout_runs(session,student,plan,snapshot,exercises,status,log,updated) VALUES(?,?,?,?,?,?,?,?)');
        foreach ($data['workout_runs'] as $row) {
            $insert->execute([$row['session'], $row['student'], $row['plan'], is_string($row['snapshot']) ? $row['snapshot'] : evo_json($row['snapshot']), is_string($row['exercises']) ? $row['exercises'] : evo_json($row['exercises']), $row['status'], $row['log'], $row['updated']]);
        }
        $db->commit();
    } catch (Throwable $e) {
        if ($db->inTransaction()) {
            $db->rollBack();
        }
        throw $e;
    } finally {
        $release = $db->prepare('SELECT RELEASE_LOCK(?)');
        $release->execute([$lockName]);
    }
    return array_map('count', array_intersect_key($data, array_flip(['users', 'plans', 'logs', 'workout_runs'])));
}
