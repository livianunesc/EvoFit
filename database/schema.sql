-- MySQL 8+ / MariaDB 10.4+; importe dentro de um banco selecionado.
-- IF NOT EXISTS preserva os dados existentes. Não contém senhas ou credenciais.
CREATE TABLE IF NOT EXISTS users (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 name TEXT NOT NULL,
 email VARCHAR(200) NOT NULL UNIQUE,
 password VARCHAR(255) NOT NULL,
 role ENUM('personal','aluno') NOT NULL,
 trainer BIGINT UNSIGNED NULL,
 goal TEXT NOT NULL,
 FOREIGN KEY (trainer) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS sessions (
 token CHAR(64) CHARACTER SET ascii PRIMARY KEY,
 user BIGINT UNSIGNED NOT NULL,
 expires DOUBLE NOT NULL,
 FOREIGN KEY (user) REFERENCES users(id) ON DELETE CASCADE,
 INDEX (expires)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS plans (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 student BIGINT UNSIGNED NOT NULL,
 kind ENUM('workout','diet') NOT NULL,
 title TEXT NOT NULL,
 items LONGTEXT NOT NULL,
 FOREIGN KEY (student) REFERENCES users(id),
 INDEX (student,kind)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS logs (
 id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
 student BIGINT UNSIGNED NOT NULL,
 kind ENUM('workout','measurement') NOT NULL,
 data LONGTEXT NOT NULL,
 date VARCHAR(32) NOT NULL DEFAULT (CURRENT_TIMESTAMP),
 FOREIGN KEY (student) REFERENCES users(id),
 INDEX (student,date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
CREATE TABLE IF NOT EXISTS workout_runs (
 session VARCHAR(100) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
 student BIGINT UNSIGNED NOT NULL,
 plan BIGINT UNSIGNED NOT NULL,
 snapshot LONGTEXT NOT NULL,
 exercises LONGTEXT NOT NULL,
 status ENUM('active','completed','invalidated') NOT NULL DEFAULT 'active',
 log BIGINT UNSIGNED NULL,
 updated DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
 active_plan BIGINT UNSIGNED GENERATED ALWAYS AS (CASE WHEN status='active' THEN plan ELSE NULL END) STORED,
 UNIQUE KEY one_active_workout (student,active_plan),
 FOREIGN KEY (student) REFERENCES users(id),
 FOREIGN KEY (plan) REFERENCES plans(id),
 FOREIGN KEY (log) REFERENCES logs(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
