-- Migration: Create concept_tags table
-- Run this against your AWS RDS MySQL instance (homework_db schema)
-- before deploying Phase 4.

CREATE DATABASE IF NOT EXISTS homework_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE homework_db;

CREATE TABLE IF NOT EXISTS concept_tags (
    id              VARCHAR(36)     NOT NULL,
    student_id      VARCHAR(128)    NOT NULL,
    session_id      VARCHAR(36)     NOT NULL,
    subject         VARCHAR(64)     NOT NULL,
    topic           VARCHAR(128)    NOT NULL,
    completed       TINYINT(1)      NOT NULL DEFAULT 0,
    steps_needed    INT             NOT NULL DEFAULT 0,
    hints_used      INT             NOT NULL DEFAULT 0,
    skips_used      INT             NOT NULL DEFAULT 0,
    struggle_index  FLOAT           NOT NULL DEFAULT 0.0,
    created_at      DATETIME(6)     NOT NULL,

    PRIMARY KEY (id),
    UNIQUE  KEY uq_session_id    (session_id),
    INDEX   idx_student_id       (student_id),
    INDEX   idx_subject_topic    (subject, topic),
    INDEX   idx_student_subject  (student_id, subject),
    INDEX   idx_created_at       (created_at)
)
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci;
