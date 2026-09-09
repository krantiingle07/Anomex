-- Users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100),
    department VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Roles table
CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL,
    description TEXT
);

-- Link users to roles
CREATE TABLE user_roles (
    user_id INT NOT NULL REFERENCES users(user_id),
    role_id INT NOT NULL REFERENCES roles(role_id),
    PRIMARY KEY (user_id, role_id)
);