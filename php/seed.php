<?php
declare(strict_types=1);
function evo_seed(PDO $db): void {
    try {
        // Advisory lock serializes repeated setup across terminals on the same database.
        $lock=evo_query($db,'SELECT GET_LOCK(?,10) AS acquired',['evofit-maintenance-'.substr(hash('sha256',getenv('DB_NAME')?:'evofit'),0,40)])->fetch();
        if ((int)$lock['acquired']!==1) throw new RuntimeException('Banco ocupado. Tente novamente.');
        $db->beginTransaction();
        if ((int)$db->query('SELECT COUNT(*) FROM users')->fetchColumn()>0) { $db->commit(); return; }
        evo_query($db,'INSERT INTO users(id,name,email,password,role,trainer,goal) VALUES(1,?,?,?,?,NULL,?)',['Livia · Personal','personal@evofit.demo',evo_password('EvoFit123!'),'personal','Acompanhar cada conquista']);
        evo_query($db,'INSERT INTO users(id,name,email,password,role,trainer,goal) VALUES(2,?,?,?,?,1,?)',['Ana Silva','aluno@evofit.demo',evo_password('EvoFit123!'),'aluno','Ganhar força e qualidade de vida']);
        $workouts=[['Segunda · Inferiores',[
            ['name'=>'Agachamento','sets'=>3,'reps'=>'12','load'=>20,'rest'=>60,'notes'=>'Mantenha a coluna neutra.'],
            ['name'=>'Leg press','sets'=>3,'reps'=>'15','load'=>60,'rest'=>60,'notes'=>'Controle a descida.']
        ]],['Quarta · Superiores',[
            ['name'=>'Remada','sets'=>3,'reps'=>'12','load'=>15,'rest'=>60,'notes'=>'Aproxime as escápulas.']
        ]]];
        foreach ($workouts as [$title,$items]) evo_query($db,'INSERT INTO plans(student,kind,title,items) VALUES(2,?,?,?)',['workout',$title,evo_json($items)]);
        evo_query($db,'INSERT INTO plans(student,kind,title,items) VALUES(2,?,?,?)',['diet','Plano equilibrado',evo_json([
            ['name'=>'Café da manhã','time'=>'07:00','food'=>'Ovos, pão integral e banana','quantity'=>'2 ovos, 2 fatias, 1 unidade'],
            ['name'=>'Almoço','time'=>'12:30','food'=>'Arroz, feijão, frango e salada','quantity'=>'100 g, 80 g, 120 g, à vontade']
        ])]);
        foreach ([['2026-09-01',72,82],['2026-10-01',71,80],['2026-11-01',70,78]] as [$date,$weight,$waist]) evo_query($db,'INSERT INTO logs(student,kind,data,date) VALUES(2,?,?,?)',['measurement',evo_json(['weight'=>$weight,'waist'=>$waist,'hip'=>98,'chest'=>90]),$date.' 00:00:00']);
        evo_query($db,'INSERT INTO logs(student,kind,data) VALUES(2,?,?)',['workout',evo_json(['title'=>'Segunda · Inferiores','exercises'=>[['name'=>'Agachamento','load'=>20,'done'=>true]],'notes'=>'Boa disposição'])]);
        $db->commit();
    } catch (Throwable $e) { if ($db->inTransaction()) $db->rollBack(); throw $e; }
    finally { evo_query($db,'SELECT RELEASE_LOCK(?)',['evofit-maintenance-'.substr(hash('sha256',getenv('DB_NAME')?:'evofit'),0,40)]); }
}
