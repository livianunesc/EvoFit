-- A conexão também precisa usar UTF-8 para preservar acentos nos clientes SQL.
SET NAMES utf8mb4;

-- EvoFit acadêmico: MySQL 8.0.16+ ou MariaDB 10.4+ (InnoDB / utf8mb4).
-- Antes de importar, selecione o banco evofit_academico. O init-db Python faz isso.
-- CREATE IF NOT EXISTS mantém os dados; não é uma migração de estrutura antiga.
-- O banco da versão PHP anterior (database/schema.sql) permanece separado.

CREATE TABLE IF NOT EXISTS usuarios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    email VARCHAR(200) NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    papel ENUM('personal', 'aluno') NOT NULL,
    personal_id BIGINT UNSIGNED NULL,
    objetivo VARCHAR(500) NOT NULL DEFAULT '',
    CONSTRAINT uq_usuarios_email UNIQUE (email),
    CONSTRAINT fk_usuarios_personal FOREIGN KEY (personal_id)
        REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_usuarios_nome CHECK (CHAR_LENGTH(TRIM(nome)) > 0),
    INDEX ix_usuarios_equipe (personal_id, papel, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS exercicios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(150) NOT NULL,
    grupo_muscular VARCHAR(80) NOT NULL,
    instrucoes VARCHAR(1000) NOT NULL DEFAULT '',
    CONSTRAINT ck_exercicios_nome CHECK (CHAR_LENGTH(TRIM(nome)) > 0),
    CONSTRAINT ck_exercicios_grupo CHECK (CHAR_LENGTH(TRIM(grupo_muscular)) > 0),
    INDEX ix_exercicios_nome (nome, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS treinos (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    aluno_id BIGINT UNSIGNED NOT NULL,
    titulo VARCHAR(150) NOT NULL,
    CONSTRAINT fk_treinos_aluno FOREIGN KEY (aluno_id)
        REFERENCES usuarios(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_treinos_titulo CHECK (CHAR_LENGTH(TRIM(titulo)) > 0),
    INDEX ix_treinos_aluno (aluno_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Entidade associativa: um treino contém vários exercícios e um exercício pode
-- participar de vários treinos. Séries/carga pertencem à prescrição, não ao catálogo.
CREATE TABLE IF NOT EXISTS treino_exercicios (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    treino_id BIGINT UNSIGNED NOT NULL,
    exercicio_id BIGINT UNSIGNED NOT NULL,
    ordem INT NOT NULL,
    series INT NOT NULL,
    repeticoes VARCHAR(30) NOT NULL,
    carga DECIMAL(8,2) NOT NULL DEFAULT 0,
    descanso INT NOT NULL DEFAULT 0,
    CONSTRAINT uq_treino_exercicios_ordem UNIQUE (treino_id, ordem),
    CONSTRAINT fk_treino_exercicios_treino FOREIGN KEY (treino_id)
        REFERENCES treinos(id) ON DELETE CASCADE ON UPDATE RESTRICT,
    CONSTRAINT fk_treino_exercicios_exercicio FOREIGN KEY (exercicio_id)
        REFERENCES exercicios(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_prescricao_ordem CHECK (ordem >= 0),
    CONSTRAINT ck_prescricao_series CHECK (series BETWEEN 1 AND 100),
    CONSTRAINT ck_prescricao_repeticoes CHECK (CHAR_LENGTH(TRIM(repeticoes)) > 0),
    CONSTRAINT ck_prescricao_carga CHECK (carga >= 0 AND carga <= 1999.99),
    CONSTRAINT ck_prescricao_descanso CHECK (descanso BETWEEN 0 AND 86400),
    INDEX ix_prescricao_exercicio (exercicio_id, treino_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Cada linha representa um treino finalizado. A data é real, em UTC, e a chave
-- única permite repetir uma requisição sem contar o mesmo treino duas vezes.
CREATE TABLE IF NOT EXISTS registros (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    treino_id BIGINT UNSIGNED NOT NULL,
    concluido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    carga_total DECIMAL(10,2) NOT NULL DEFAULT 0,
    chave VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    CONSTRAINT uq_registros_chave UNIQUE (chave),
    CONSTRAINT fk_registros_treino FOREIGN KEY (treino_id)
        REFERENCES treinos(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT ck_registros_carga CHECK (carga_total >= 0),
    INDEX ix_registros_data (concluido_em, id),
    INDEX ix_registros_treino (treino_id, id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
