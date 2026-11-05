<?php
declare(strict_types=1);
require_once __DIR__.'/bootstrap.php';
function evo_cookie(string $token,int $expires): void {
    $script=str_replace('\\','/',$_SERVER['SCRIPT_NAME']??'/api.php');
    // Match the frontend directory when installed under /EvoFit/static on XAMPP.
    $path=str_contains($script,'api.php') ? rtrim(dirname($script),'/').'/' : '/';
    if ($path==='./') $path='/';
    setcookie('evofit_session',$token,['expires'=>$expires,'path'=>$path,'secure'=>getenv('SECURE_COOKIE')==='1','httponly'=>true,'samesite'=>'Strict']);
}
function evo_user_public(array $u): array { return ['id'=>(int)$u['id'],'name'=>$u['name'],'email'=>$u['email'],'role'=>$u['role'],'goal'=>$u['goal']]; }
function evo_credentials(array $b): array {
    $email=strtolower(evo_text($b['email']??'',200,true));
    $password=$b['password']??''; $role=$b['role']??'';
    if (!filter_var($email,FILTER_VALIDATE_EMAIL) || !is_string($password) || strlen($password)<8 || strlen($password)>512 || !in_array($role,['personal','aluno'],true)) throw new ApiError('Informe e-mail válido, perfil e senha com ao menos 8 caracteres.');
    return [$email,$password,$role];
}
function evo_route(PDO $db,string $route,string $method,array $b): array {
    if ($route==='login' || $route==='register') {
        [$email,$pw,$role]=evo_credentials($b);
        if ($route==='register') {
            $name=evo_text($b['name']??'',150,true);
            try { evo_query($db,'INSERT INTO users(name,email,password,role,trainer,goal) VALUES(?,?,?,?,NULL,?)',[$name,$email,evo_password($pw),$role,'']); }
            catch (PDOException $e) { if (($e->errorInfo[1]??0)===1062) throw new ApiError('Este e-mail já está cadastrado.'); throw $e; }
        }
        $user=evo_query($db,'SELECT * FROM users WHERE email=?',[$email])->fetch();
        if (!$user || $user['role']!==$role || !evo_verify_password($pw,$user['password'])) throw new ApiError('E-mail, senha ou perfil incorretos.',401);
        if (evo_needs_rehash($user['password'])) evo_query($db,'UPDATE users SET password=? WHERE id=?',[evo_password($pw),$user['id']]);
        $token=bin2hex(random_bytes(32)); $expires=time()+86400;
        evo_query($db,'INSERT INTO sessions(token,user,expires) VALUES(?,?,?)',[hash('sha256',$token),$user['id'],$expires]);
        evo_cookie($token,$expires);
        return ['ok'=>true];
    }
    $token=$_COOKIE['evofit_session']??'';
    if (!is_string($token) || strlen($token)>128) throw new ApiError('Entre para continuar.',401);
    $user=evo_query($db,'SELECT u.* FROM users u JOIN sessions s ON u.id=s.user WHERE s.token=? AND s.expires>?',[hash('sha256',$token),time()])->fetch();
    if (!$user) throw new ApiError('Entre para continuar.',401);
    $user['id']=(int)$user['id'];
    if ($route==='logout') {
        evo_query($db,'DELETE FROM sessions WHERE token=?',[hash('sha256',$token)]); evo_cookie('',time()-3600); return ['ok'=>true];
    }
    if ($route==='state') {
        $students=$user['role']==='personal' ? evo_query($db,'SELECT id,name,email,goal FROM users WHERE trainer=? ORDER BY id',[$user['id']])->fetchAll() : [['id'=>$user['id'],'name'=>$user['name'],'email'=>$user['email'],'goal'=>$user['goal']]];
        $plans=[];$logs=[];$progress=[];
        foreach ($students as &$student) {
            $student['id']=(int)$student['id'];
            foreach (evo_query($db,'SELECT * FROM plans WHERE student=? ORDER BY id',[$student['id']])->fetchAll() as $plan) {
                $plan['id']=(int)$plan['id'];$plan['student']=(int)$plan['student'];$plan['items']=evo_decode($plan['items']);
                if ($plan['kind']==='workout') $plan['version']=evo_version($plan['items']);
                $plans[]=$plan;
            }
            foreach (evo_query($db,'SELECT * FROM logs WHERE student=? ORDER BY date,id',[$student['id']])->fetchAll() as $log) { $log['id']=(int)$log['id'];$log['student']=(int)$log['student'];$log['data']=evo_decode($log['data']);$logs[]=$log; }
            foreach (evo_query($db,"SELECT * FROM workout_runs WHERE student=? AND status='active' ORDER BY updated",[$student['id']])->fetchAll() as $run) $progress[]=evo_progress($run);
        }
        return ['user'=>evo_user_public($user),'students'=>$students,'plans'=>$plans,'logs'=>$logs,'workoutProgress'=>$progress];
    }
    if ($route==='exercise' || $route==='workout/complete') return evo_workout($db,$user,$route,$b);
    if ($route==='student') {
        evo_require_role($user,'personal');
        [$email,$pw,$role]=evo_credentials(['email'=>$b['email']??'','password'=>$b['password']??'','role'=>'aluno']);
        $name=evo_text($b['name']??'',150,true);$goal=evo_text($b['goal']??'',5000);
        try { evo_query($db,'INSERT INTO users(name,email,password,role,trainer,goal) VALUES(?,?,?,?,?,?)',[$name,$email,evo_password($pw),'aluno',$user['id'],$goal]); }
        catch (PDOException $e) { if (($e->errorInfo[1]??0)===1062) throw new ApiError('E-mail já cadastrado. Use outro e-mail para o novo aluno.');throw $e; }
        return ['ok'=>true];
    }
    if ($route==='profile') {
        evo_query($db,'UPDATE users SET name=?,goal=? WHERE id=?',[evo_text($b['name']??'',150,true),evo_text($b['goal']??'',5000),$user['id']]);return ['ok'=>true];
    }
    if ($route==='plan') return evo_plan($db,$user,$b);
    if ($route==='log') return evo_log($db,$user,$b);
    throw new ApiError('Página não encontrada.',404);
}
function evo_workout(PDO $db,array $user,string $route,array $b): array {
    evo_require_role($user,'aluno');
    if (isset($b['student']) && $b['student']!==$user['id']) throw new ApiError('Acesso negado.',403);
    if (!is_int($b['plan']??null) || $b['plan']<1) throw new ApiError('Treino inválido.');
    $db->beginTransaction();
    try {
        // Lock the plan first in every writer to serialize exercise edits and completion.
        $plan=evo_query($db,"SELECT * FROM plans WHERE id=? AND student=? AND kind='workout' FOR UPDATE",[$b['plan'],$user['id']])->fetch();
        if (!$plan) throw new ApiError('Treino não encontrado.',404);
        $expected=evo_decode($plan['items']);
        if ($route==='exercise' && ($b['version']??null)!==evo_version($expected)) throw new ApiError('O treino foi atualizado. Reabra o treino para ver os exercícios atuais.',409);
        $session=$b['session']??null;
        if ($session!==null && (!is_string($session) || $session==='' || strlen($session)>100)) throw new ApiError('Sessão de treino inválida.');
        $run=$session ? evo_query($db,'SELECT * FROM workout_runs WHERE session=? AND student=? AND plan=? FOR UPDATE',[$session,$user['id'],$plan['id']])->fetch() : evo_query($db,"SELECT * FROM workout_runs WHERE student=? AND plan=? AND status='active' FOR UPDATE",[$user['id'],$plan['id']])->fetch();
        if ($route==='workout/complete') {
            if (!$session || !$run) throw new ApiError('Retome o treino antes de concluir.',409);
            if ($run['status']==='completed') { $db->commit();return ['ok'=>true,'log'=>(int)$run['log'],'alreadyCompleted'=>true]; }
        }
        if (($session && !$run) || ($run && ($run['status']!=='active' || evo_snapshot(evo_decode($run['snapshot']))!==evo_snapshot($expected)))) throw new ApiError('O treino foi atualizado. Reabra para iniciar uma nova sessão.',409);
        if ($route==='exercise') {
            $index=$b['index']??null;
            if (!is_int($index) || $index<0 || $index>=count($expected) || !is_bool($b['done']??null)) throw new ApiError('Exercício ou conclusão inválidos.');
            $load=evo_number($b['load']??null,0,1999.999999,true);
            if (!$run) {
                $session=bin2hex(random_bytes(24));
                $exercises=array_map(fn($x)=>['load'=>(float)$x['load'],'done'=>false],$expected);
                evo_query($db,'INSERT INTO workout_runs(session,student,plan,snapshot,exercises) VALUES(?,?,?,?,?)',[$session,$user['id'],$plan['id'],evo_json(evo_snapshot($expected)),evo_json($exercises)]);
            } else { $session=$run['session'];$exercises=evo_decode($run['exercises']); }
            $exercises[$index]=['load'=>$load,'done'=>$b['done']];
            evo_query($db,'UPDATE workout_runs SET exercises=?,updated=CURRENT_TIMESTAMP WHERE session=?',[evo_json($exercises),$session]);
            $updated=evo_query($db,'SELECT * FROM workout_runs WHERE session=?',[$session])->fetch();
            $db->commit();return ['ok'=>true,'progress'=>evo_progress($updated)];
        }
        $exercises=evo_decode($run['exercises']);
        if (count($exercises)!==count($expected) || count(array_filter($exercises,fn($x)=>($x['done']??false)===true))!==count($expected)) throw new ApiError('Conclua todos os exercícios antes de finalizar o treino.');
        $notes=evo_text($b['notes']??'',5000);
        $data=['title'=>$plan['title'],'exercises'=>[],'notes'=>$notes];
        foreach ($expected as $i=>$item) $data['exercises'][]=['name'=>$item['name'],'load'=>$exercises[$i]['load'],'done'=>true];
        evo_query($db,"INSERT INTO logs(student,kind,data) VALUES(?,'workout',?)",[$user['id'],evo_json($data)]);$id=(int)$db->lastInsertId();
        evo_query($db,"UPDATE workout_runs SET status='completed',log=?,updated=CURRENT_TIMESTAMP WHERE session=?",[$id,$session]);
        $db->commit();return ['ok'=>true,'log'=>$id,'alreadyCompleted'=>false];
    } catch (Throwable $e) { if ($db->inTransaction()) $db->rollBack();throw $e; }
}
function evo_plan(PDO $db,array $user,array $b): array {
    evo_require_role($user,'personal');$sid=evo_id($b['student']??$user['id']);evo_student($db,$user,$sid);
    $kind=$b['kind']??null;$title=evo_text($b['title']??'',200,true);$items=$b['items']??null;
    if (!in_array($kind,['workout','diet'],true) || !is_array($items) || !array_is_list($items) || count($items)<1 || count($items)>100) throw new ApiError('Preencha o título e ao menos um item.');
    foreach ($items as $item) {
        if (!is_array($item)) throw new ApiError('Item inválido.');
        evo_text($item['name']??'',200,true);
        if ($kind==='workout') {
            $reps=$item['reps']??'';
            if (!is_string($reps) && !is_int($reps) && !(is_float($reps) && is_finite($reps))) throw new ApiError('Informe repetições válidas.');
            evo_number($item['sets']??null,1,1000);evo_number($item['load']??null,0,1999.999999);evo_number($item['rest']??null,0,86400);evo_text((string)$reps,100,true);evo_text($item['notes']??'',5000);
        }
        else { foreach (['food','quantity','time'] as $key) evo_text($item[$key]??'',5000,true); }
    }
    if ($kind==='workout') evo_snapshot($items);
    $db->beginTransaction();
    try {
        if (isset($b['id']) && $b['id']) {
            $id=evo_id($b['id']);$previous=evo_query($db,'SELECT items FROM plans WHERE id=? AND student=? AND kind=? FOR UPDATE',[$id,$sid,$kind])->fetch();
            if (!$previous) throw new ApiError('Plano não encontrado.',404);
            evo_query($db,'UPDATE plans SET title=?,items=? WHERE id=?',[$title,evo_json($items),$id]);
            if ($kind==='workout' && evo_snapshot(evo_decode($previous['items']))!==evo_snapshot($items)) evo_query($db,"UPDATE workout_runs SET status='invalidated',updated=CURRENT_TIMESTAMP WHERE plan=? AND status='active'",[$id]);
        } else evo_query($db,'INSERT INTO plans(student,kind,title,items) VALUES(?,?,?,?)',[$sid,$kind,$title,evo_json($items)]);
        $db->commit();return ['ok'=>true];
    } catch (Throwable $e) { if ($db->inTransaction()) $db->rollBack();throw $e; }
}
function evo_log(PDO $db,array $user,array $b): array {
    evo_require_role($user,'aluno');$sid=evo_id($b['student']??$user['id']);evo_student($db,$user,$sid);
    $kind=$b['kind']??null;$data=$b['data']??null;
    if (!is_array($data) || array_is_list($data)) throw new ApiError('Registro inválido.');
    if ($kind==='measurement') foreach (['weight','waist','hip','chest'] as $key) $data[$key]=evo_number($data[$key]??null,0.000001,499.999999);
    elseif ($kind==='workout') {
        $plan=evo_query($db,"SELECT * FROM plans WHERE id=? AND student=? AND kind='workout'",[evo_id($b['plan']??null),$sid])->fetch();
        if (!$plan) throw new ApiError('Treino não encontrado.',404);
        $expected=evo_decode($plan['items']);$exercises=$data['exercises']??null;
        if (!is_array($exercises) || !array_is_list($exercises) || count($exercises)!==count($expected)) throw new ApiError('Marque todos os exercícios e informe as cargas para concluir.');
        foreach ($exercises as $i=>&$exercise) {
            if (!is_array($exercise) || ($exercise['done']??false)!==true) throw new ApiError('Conclua todos os exercícios.');
            $exercise['load']=evo_number($exercise['load']??null,0,1999.999999);$exercise['name']=$expected[$i]['name'];
        }
        unset($exercise);$data['exercises']=$exercises;$data['title']=$plan['title'];$data['notes']=evo_text($data['notes']??'',5000);
    } else throw new ApiError('Registro inválido.');
    evo_query($db,'INSERT INTO logs(student,kind,data) VALUES(?,?,?)',[$sid,$kind,evo_json($data)]);return ['ok'=>true];
}
function evo_handle(): void {
    header('Content-Type: application/json; charset=utf-8');header('Cache-Control: no-store');header('X-Content-Type-Options: nosniff');
    try {
        $method=$_SERVER['REQUEST_METHOD']??'GET';
        if (!is_string($_GET['route']??'')) throw new ApiError('Página não encontrada.',404);
        $route=trim($_GET['route']??'','/');
        if (!preg_match('~^[a-z]+(?:/[a-z]+)*$~D',$route)) throw new ApiError('Página não encontrada.',404);
        $routes=['login','register','logout','state','student','profile','plan','log','exercise','workout/complete'];
        if (!in_array($route,$routes,true)) throw new ApiError('Página não encontrada.',404);
        if ($method!==($route==='state'?'GET':'POST')) throw new ApiError($route==='state'?'Use GET para consultar.':'Use POST para alterar registros.',405);
        $b=[];
        if ($method==='POST') {
            if (($_SERVER['HTTP_SEC_FETCH_SITE']??'')==='cross-site') throw new ApiError('Origem não autorizada.',403);
            if (!str_starts_with(strtolower($_SERVER['CONTENT_TYPE']??''),'application/json')) throw new ApiError('Envie dados JSON.',415);
            if ((int)($_SERVER['CONTENT_LENGTH']??0)>100000) throw new ApiError('Dados muito grandes.',413);
            $raw=file_get_contents('php://input',false,null,0,100001);
            if ($raw===false || strlen($raw)>100000) throw new ApiError('Dados muito grandes.',413);
            $body=json_decode($raw,false,512,JSON_THROW_ON_ERROR);
            if (!$body instanceof stdClass) throw new ApiError('Dados inválidos.');
            $b=json_decode($raw,true,512,JSON_THROW_ON_ERROR);
        }
        $result=evo_route(evo_db(),$route,$method,$b);echo evo_json($result);
    } catch (ApiError $e) { http_response_code($e->status);echo evo_json(['error'=>$e->getMessage()]); }
    catch (JsonException|TypeError|ValueError $e) { http_response_code(400);echo evo_json(['error'=>'Confira os campos informados.']); }
    catch (Throwable $e) { http_response_code(503);echo evo_json(['error'=>'Não foi possível acessar o serviço. Verifique a configuração do banco e tente novamente.']); }
}
