-- seed_app_users.sql
-- M6: one synthetic user per security role (guides/standards.md#security-roles-m6).
-- DEV/TEST ONLY. Password for every user below is "Capstone#2026" (database/README.md).
-- Re-runnable: ON CONFLICT upserts the hash/role instead of erroring on a second run.

INSERT INTO app_user (username, password_hash, role) VALUES
    ('admin@capstone.local',       '$2b$10$R1HO7xoXtnSsD1Gtd.1NuuSsqv07oXg0akMn4CanJofZVj.rZYK0e', 'ADMIN'),
    ('underwriter@capstone.local', '$2b$10$R1HO7xoXtnSsD1Gtd.1NuuSsqv07oXg0akMn4CanJofZVj.rZYK0e', 'UNDERWRITER'),
    ('servicing@capstone.local',   '$2b$10$R1HO7xoXtnSsD1Gtd.1NuuSsqv07oXg0akMn4CanJofZVj.rZYK0e', 'SERVICING_AGENT'),
    ('risk@capstone.local',        '$2b$10$R1HO7xoXtnSsD1Gtd.1NuuSsqv07oXg0akMn4CanJofZVj.rZYK0e', 'RISK_ANALYST'),
    ('support@capstone.local',     '$2b$10$R1HO7xoXtnSsD1Gtd.1NuuSsqv07oXg0akMn4CanJofZVj.rZYK0e', 'SUPPORT')
ON CONFLICT (username) DO UPDATE SET password_hash = EXCLUDED.password_hash, role = EXCLUDED.role;
