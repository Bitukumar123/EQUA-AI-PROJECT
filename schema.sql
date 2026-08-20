-- EduAI Platform — MySQL Schema
-- Run this once against your MySQL server:
--   mysql -u root -p < schema.sql

CREATE DATABASE IF NOT EXISTS eduai_platform CHARACTER SET utf8mb4;
USE eduai_platform;

-- 1. Institutions (College / School registration)
CREATE TABLE IF NOT EXISTS institutions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    institution_name VARCHAR(150) NOT NULL,
    institution_code VARCHAR(30) NOT NULL UNIQUE,   -- the "ID" the institution logs in with
    password_hash VARCHAR(255) NOT NULL,
    address VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Principals (belongs to one institution)
CREATE TABLE IF NOT EXISTS principals (
    id INT AUTO_INCREMENT PRIMARY KEY,
    institution_id INT NOT NULL,
    principal_id VARCHAR(30) NOT NULL UNIQUE,       -- login ID
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE
);

-- 3. Students (belongs to one institution)
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    institution_id INT NOT NULL,
    student_id VARCHAR(30) NOT NULL UNIQUE,         -- login ID
    full_name VARCHAR(100) NOT NULL,
    class_name VARCHAR(50),
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE
);

-- 4. Parents (linked to one student)
CREATE TABLE IF NOT EXISTS parents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    parent_login_id VARCHAR(30) NOT NULL UNIQUE,    -- login ID
    full_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 5. Attendance (one row per student per day)
CREATE TABLE IF NOT EXISTS attendance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    attendance_date DATE NOT NULL,
    status ENUM('present','absent','late') NOT NULL DEFAULT 'present',
    marked_by INT,                                  -- principals.id
    UNIQUE KEY unique_day (student_id, attendance_date),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 6. AI-generated exams
CREATE TABLE IF NOT EXISTS exams (
    id INT AUTO_INCREMENT PRIMARY KEY,
    institution_id INT NOT NULL,
    subject VARCHAR(100) NOT NULL,
    topic VARCHAR(150),
    difficulty VARCHAR(20) DEFAULT 'medium',
    questions_json JSON NOT NULL,                    -- AI-generated Q&A + correct answers
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (institution_id) REFERENCES institutions(id) ON DELETE CASCADE
);

-- 7. Exam attempts / results
CREATE TABLE IF NOT EXISTS exam_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    exam_id INT NOT NULL,
    student_id INT NOT NULL,
    answers_json JSON,
    score DECIMAL(5,2),
    max_score DECIMAL(5,2),
    ai_feedback TEXT,
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (exam_id) REFERENCES exams(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 8. AI Teacher chat history (also powers the whiteboard session log)
CREATE TABLE IF NOT EXISTS chat_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    role ENUM('user','assistant') NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Helpful indexes
CREATE INDEX idx_attendance_student_date ON attendance(student_id, attendance_date);
CREATE INDEX idx_chat_student ON chat_history(student_id, created_at);
CREATE INDEX idx_results_student ON exam_results(student_id);
