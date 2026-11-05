<?php
// Configuração privada: nunca coloque este diretório no document root público.
declare(strict_types=1);
const EVO_ROOT = __DIR__ . '/..';
final class ApiError extends RuntimeException {
    public int $status;
    public function __construct(string $message, int $status=400) { parent::__construct($message); $this->status=$status; }
}
function evo_load_env(): void {
    $file = EVO_ROOT . '/.env';
    if (!is_file($file)) return;
    foreach (file($file, FILE_IGNORE_NEW_LINES) ?: [] as $line) {
        $line=trim($line);
        if ($line==='' || str_starts_with($line,'#') || !str_contains($line,'=')) continue;
        [$name,$value]=explode('=',$line,2); $name=trim($name); $value=trim($value);
        if (!preg_match('/^[A-Za-z_][A-Za-z0-9_]*$/D',$name) || getenv($name)!==false) continue;
        if (strlen($value)>=2 && (($value[0]==='"' && str_ends_with($value,'"')) || ($value[0]==="'" && str_ends_with($value,"'")))) $value=substr($value,1,-1);
        putenv($name.'='.$value);
    }
}
evo_load_env();
date_default_timezone_set(getenv('APP_TIMEZONE') ?: 'America/Sao_Paulo');
function evo_json(mixed $value): string { return json_encode($value,JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR); }
function evo_decode(string $value): mixed { return json_decode($value,true,512,JSON_THROW_ON_ERROR); }
function evo_db(bool $selectDatabase=true): PDO {
    if (!extension_loaded('pdo_mysql')) throw new RuntimeException('Ative a extensão pdo_mysql do PHP.');
    $name=getenv('DB_NAME') ?: 'evofit';
    if (!preg_match('/^[A-Za-z0-9_]+$/D',$name)) throw new RuntimeException('DB_NAME inválido. Use letras, números e sublinhado.');
    $port=getenv('DB_PORT') ?: '3306';
    if (!ctype_digit($port) || (int)$port<1 || (int)$port>65535) throw new RuntimeException('DB_PORT inválido.');
    $socket=getenv('DB_SOCKET');
    $dsn=$socket ? 'mysql:unix_socket='.$socket : 'mysql:host='.(getenv('DB_HOST') ?: '127.0.0.1').';port='.$port;
    if ($selectDatabase) $dsn.=';dbname='.$name;
    $dsn.=';charset=utf8mb4';
    $pdo=new PDO($dsn,getenv('DB_USER')!==false ? getenv('DB_USER') : 'root',getenv('DB_PASSWORD') ?: '',[
        PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,
        PDO::ATTR_EMULATE_PREPARES=>false,PDO::ATTR_STRINGIFY_FETCHES=>false,
    ]);
    $pdo->exec("SET time_zone='+00:00'");
    return $pdo;
}
function evo_schema(PDO $db): void {
    $sql=file_get_contents(EVO_ROOT.'/database/schema.sql');
    if ($sql===false) throw new RuntimeException('Arquivo de esquema ausente.');
    foreach (explode(';',preg_replace('/^\s*--.*$/m','',$sql)) as $statement) { if (trim($statement)!=='') $db->exec($statement); }
}
function evo_query(PDO $db,string $sql,array $params=[]): PDOStatement { $s=$db->prepare($sql); $s->execute($params); return $s; }
function evo_snapshot(array $items): array {
    $result=[];
    foreach ($items as $item) {
        if (!is_array($item)) throw new ApiError('Exercício inválido.');
        $row=[];
        // Sorted field order and JSON_PRESERVE_ZERO_FRACTION match legacy Python hashes.
        foreach (['load','name','notes','reps','rest','sets'] as $key) {
            if (in_array($key,['sets','load','rest'],true)) {
                $value=$item[$key]??0;
                if (is_bool($value) || !is_numeric($value) || !is_finite((float)$value)) throw new ApiError('Confira séries, carga e descanso.');
                $row[$key]=(float)$value;
            } else {
                $value=$item[$key]??'';
                if (!is_string($value) && !is_numeric($value)) throw new ApiError('Confira as instruções do exercício.');
                $row[$key]=trim((string)$value);
            }
        }
        $result[]=$row;
    }
    return $result;
}
function evo_version(array $items): string {
    return hash('sha256',json_encode(evo_snapshot($items),JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_PRESERVE_ZERO_FRACTION|JSON_THROW_ON_ERROR));
}
function evo_progress(array $run): array {
    return ['student'=>(int)$run['student'],'plan'=>(int)$run['plan'],'session'=>$run['session'],'exercises'=>evo_decode($run['exercises']),'updated'=>$run['updated']];
}
function evo_password(string $plain): string {
    // Fixed-size SHA-256 hex input avoids bcrypt's 72-byte truncation and NUL limitation.
    return 'sha256:'.password_hash(hash('sha256',$plain),PASSWORD_DEFAULT);
}
function evo_needs_rehash(string $stored): bool {
    return !str_starts_with($stored,'sha256:') || password_needs_rehash(substr($stored,7),PASSWORD_DEFAULT);
}
function evo_verify_password(string $plain,string $stored): bool {
    if (str_starts_with($stored,'sha256:')) return password_verify(hash('sha256',$plain),substr($stored,7));
    if (!preg_match('/^[a-f0-9]{32}:[a-f0-9]{128}$/D',$stored)) return password_verify($plain,$stored);
    // Migração gradual: credenciais nunca são colocadas em argumentos ou logs.
    if (!function_exists('proc_open')) throw new ApiError('O primeiro acesso de uma conta migrada requer Python habilitado no servidor.',503);
    $python=getenv('PYTHON_BIN') ?: (PHP_OS_FAMILY==='Windows' ? 'python' : 'python3');
    $process=proc_open([$python,EVO_ROOT.'/tools/verify_legacy_password.py'],[['pipe','r'],['pipe','w'],['pipe','w']],$pipes,null,null,['bypass_shell'=>true]);
    if (!is_resource($process)) throw new ApiError('Python indisponível para validar a conta migrada.',503);
    fwrite($pipes[0],evo_json(['password'=>$plain,'hash'=>$stored])); fclose($pipes[0]);
    stream_set_timeout($pipes[1],10); $answer=stream_get_contents($pipes[1]); fclose($pipes[1]); fclose($pipes[2]);
    $status=proc_close($process);
    if ($status!==0) throw new ApiError('Não foi possível validar a senha migrada. Verifique a configuração de Python.',503);
    return trim((string)$answer)==='1';
}
function evo_require_role(array $user,string $role): void { if ($user['role']!==$role) throw new ApiError('Acesso restrito ao perfil autorizado.',403); }
function evo_text(mixed $value,int $max=200,bool $required=false): string {
    if (!is_string($value)) throw new ApiError('Confira os campos de texto.');
    $value=trim($value);
    if (($required && $value==='') || strlen($value)>$max) throw new ApiError('Confira os campos obrigatórios e o tamanho dos textos.');
    return $value;
}
function evo_number(mixed $value,float $min,float $max,bool $strict=false): float {
    if (is_bool($value) || ($strict && !is_int($value) && !is_float($value)) || !is_numeric($value) || !is_finite((float)$value) || (float)$value<$min || (float)$value>$max) throw new ApiError('Informe valores numéricos válidos.');
    return (float)$value;
}
function evo_id(mixed $value): int {
    if (is_bool($value) || (!is_int($value) && !(is_string($value) && ctype_digit($value))) || (int)$value<1) throw new ApiError('Identificador inválido.');
    return (int)$value;
}
function evo_student(PDO $db,array $user,int $id): void {
    if ($user['role']==='aluno') { if ($id!==(int)$user['id']) throw new ApiError('Acesso negado.',403); }
    elseif (!evo_query($db,'SELECT id FROM users WHERE id=? AND trainer=? AND role=?',[$id,$user['id'],'aluno'])->fetch()) throw new ApiError('Acesso negado.',403);
}
