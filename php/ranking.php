<?php
declare(strict_types=1);

/** Return the local calendar month and its UTC database boundaries. */
function evo_ranking_window(?DateTimeImmutable $now=null, ?DateTimeZone $zone=null): array {
    $zone ??= new DateTimeZone(getenv('APP_TIMEZONE') ?: 'America/Sao_Paulo');
    $local=($now ?? new DateTimeImmutable('now'))->setTimezone($zone);
    $start=$local->modify('first day of this month')->setTime(0,0,0);
    $end=$start->modify('first day of next month');
    $utc=new DateTimeZone('UTC');
    return [
        'month'=>$start->format('Y-m'),
        'start'=>$start->setTimezone($utc)->format('Y-m-d H:i:s'),
        'end'=>$end->setTimezone($utc)->format('Y-m-d H:i:s'),
    ];
}

/**
 * Only disclose leaderboard names and aggregate workout totals within the authenticated team.
 * Rankings are dense (1,1,2); equal totals are displayed in stable ascending student-ID order.
 */
function evo_team_ranking(PDO $db,array $user,mixed $period='month'): array {
    if (!is_string($period) || !in_array($period,['month','all'],true)) throw new ApiError('Escolha o ranking do mês ou de todo o período.');
    $window=evo_ranking_window();
    $result=['trainer'=>null,'title'=>'Equipe ainda não vinculada','period'=>$period,'month'=>$window['month'],'members'=>[],'totalCompleted'=>0];
    // The caller cannot select another trainer: derive the team exclusively from stored identity.
    $trainerId=$user['role']==='personal' ? (int)$user['id'] : ($user['trainer']===null ? null : (int)$user['trainer']);
    if ($trainerId===null) return $result;
    $trainer=evo_query($db,"SELECT id,name FROM users WHERE id=? AND role='personal'",[$trainerId])->fetch();
    if (!$trainer) return $result;
    $result['trainer']=['id'=>(int)$trainer['id'],'name'=>$trainer['name']];
    $result['title']='TEAM '.$trainer['name'].' FOCUS';
    $timeFilter='';$params=[];
    if ($period==='month') {
        // Normalize migrated YYYY-MM-DD rows to midnight UTC before comparing calendar bounds.
        $timeFilter=' AND CAST(l.date AS DATETIME)>=? AND CAST(l.date AS DATETIME)<?';
        $params=[$window['start'],$window['end']];
    }
    $params[]=$trainerId;
    $rows=evo_query($db,"SELECT u.id,u.name,COUNT(l.id) AS completed
        FROM users u LEFT JOIN logs l ON l.student=u.id AND l.kind='workout'".$timeFilter."
        WHERE u.role='aluno' AND u.trainer=?
        GROUP BY u.id,u.name ORDER BY completed DESC,u.id ASC",$params)->fetchAll();
    $position=0;$previous=null;
    foreach ($rows as $row) {
        $completed=(int)$row['completed'];
        if ($previous===null || $completed!==$previous) $position++;
        $result['members'][]=[
            'student'=>(int)$row['id'],'name'=>$row['name'],'completed'=>$completed,
            'position'=>$position,'isCurrent'=>$user['role']==='aluno' && (int)$row['id']===(int)$user['id'],
        ];
        $result['totalCompleted']+=$completed;$previous=$completed;
    }
    return $result;
}
