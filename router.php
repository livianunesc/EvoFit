<?php
// Roteador exclusivo do servidor de desenvolvimento PHP; document root: static/.
declare(strict_types=1);
$path=rawurldecode(parse_url($_SERVER['REQUEST_URI']??'/',PHP_URL_PATH) ?: '/');
if (str_starts_with($path,'/api/')) {
    $_GET['route']=substr($path,5);$_SERVER['SCRIPT_NAME']='/api.php';require __DIR__.'/static/api.php';return true;
}
if ($path==='/api.php') { $_SERVER['SCRIPT_NAME']='/api.php';require __DIR__.'/static/api.php';return true; }
if ($path==='/' || $path==='/index.html') { header('Content-Type: text/html; charset=utf-8');readfile(__DIR__.'/static/index.html');return true; }
$allowed=['/app.js'=>'text/javascript; charset=utf-8','/workouts.js'=>'text/javascript; charset=utf-8','/style.css'=>'text/css; charset=utf-8','/workouts.css'=>'text/css; charset=utf-8'];
if (isset($allowed[$path])) { header('Content-Type: '.$allowed[$path]);readfile(__DIR__.'/static'.$path);return true; }
if (preg_match('~^/fonts/[a-z0-9-]+\.ttf$~D',$path) && is_file(__DIR__.'/static'.$path)) { header('Content-Type: font/ttf');readfile(__DIR__.'/static'.$path);return true; }
if (preg_match('~^/images/[a-z0-9-]+\.(?:svg|png)$~D',$path) && is_file(__DIR__.'/static'.$path)) { header('Content-Type: '.(str_ends_with($path,'.png')?'image/png':'image/svg+xml'));readfile(__DIR__.'/static'.$path);return true; }
http_response_code(404);header('Content-Type: text/plain; charset=utf-8');echo 'Página não encontrada.';return true;
