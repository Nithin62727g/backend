-- ============================================================
--  MasterAI Database Schema
--  Compatible with: MariaDB / MySQL (XAMPP)
--  Import via phpMyAdmin or:
--    mysql -u root -p < database.sql
-- ============================================================

CREATE DATABASE IF NOT EXISTS masterai_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE masterai_db;

-- ------------------------------------------------------------
-- USERS
-- Stores registered user accounts.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INT             AUTO_INCREMENT PRIMARY KEY,
    email           VARCHAR(255)    NOT NULL UNIQUE,
    hashed_password VARCHAR(255)    NOT NULL,
    name            VARCHAR(255)    NOT NULL,
    goal            VARCHAR(255)    NULL,
    learning_style  VARCHAR(100)    NOT NULL DEFAULT 'Visual Learner',
    experience_level VARCHAR(100)   NULL,
    weekly_hours    INT             NULL,
    target_completion VARCHAR(100)  NULL,
    xp              INT             NOT NULL DEFAULT 0,
    current_streak  INT             NOT NULL DEFAULT 0,
    longest_streak  INT             NOT NULL DEFAULT 0,
    last_login_date DATE            NULL,
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- ROADMAPS
-- Stores AI-generated learning roadmaps linked to a user.
-- The full roadmap structure is stored as JSON in `data`.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS roadmaps (
    id          INT             AUTO_INCREMENT PRIMARY KEY,
    user_id     INT             NULL,
    goal_title  VARCHAR(255)    NOT NULL,
    data        JSON            NOT NULL,
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- QUIZ RESULTS
-- Stores quiz scores submitted by users.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quiz_results (
    id          INT         AUTO_INCREMENT PRIMARY KEY,
    user_id     INT         NULL,
    topic       VARCHAR(255) NOT NULL,
    score       INT         NOT NULL,
    max_score   INT         NOT NULL,
    xp_earned   INT         NOT NULL DEFAULT 0,
    passed      TINYINT(1)  NOT NULL DEFAULT 0,
    taken_at    DATETIME    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ------------------------------------------------------------
-- TOPIC PROGRESS
-- Tracks which roadmap topics a user has completed.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS topic_progress (
    id          INT         AUTO_INCREMENT PRIMARY KEY,
    user_id     INT         NOT NULL,
    topic_id    VARCHAR(255) NOT NULL,
    xp_earned   INT         NOT NULL DEFAULT 50,
    completed_at DATETIME   NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_user_topic (user_id, topic_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
