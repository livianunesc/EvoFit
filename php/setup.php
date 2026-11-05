<?php
declare(strict_types=1);
require __DIR__.'/bootstrap.php';
if (PHP_SAPI!=='cli') { http_response_code(404); exit; }
try {
    $args=array_slice($argv,1);
    foreach ($args as $arg) if (!in_array($arg,['--create-database','--no-seed','--check'],true)) throw new RuntimeException('Opção de preparação desconhecida.');
    if (in_array('--check',$args,true)) {
        $db=evo_db();
        foreach (['users','sessions','plans','logs','workout_runs'] as $table) $db->query('SELECT 1 FROM '.$table.' LIMIT 1');
        fwrite(STDOUT,"Conexão MySQL e tabelas prontas.\n"); exit(0);
    }
    if (in_array('--create-database',$args,true)) {
        $db=evo_db(false); $name=getenv('DB_NAME') ?: 'evofit';
        $db->exec('CREATE DATABASE IF NOT EXISTS `'.$name.'` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci');
    }
    $db=evo_db(); evo_schema($db);
    if (!in_array('--no-seed',$args,true)) { require __DIR__.'/seed.php'; evo_seed($db); }
    fwrite(STDOUT,"Banco preparado sem apagar registros existentes.\n");
} catch (Throwable $e) {
    fwrite(STDERR,"Falha ao preparar MySQL. Confira o serviço, DB_HOST/DB_PORT, banco, usuário, senha e extensão pdo_mysql.\n");
    if ($e instanceof ApiError) fwrite(STDERR,$e->getMessage()."\n");
    if ($e instanceof PDOException) fwrite(STDERR,'Código MySQL: '.(string)($e->errorInfo[1]??$e->getCode())."\n");
    exit(1);
}
