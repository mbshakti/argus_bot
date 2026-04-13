CREATE TABLE IF NOT EXISTS messages (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    deliver_at TIMESTAMP DEFAULT NOW(),
    msg_type TEXT DEFAULT 'response'
);

CREATE TABLE IF NOT EXISTS state (
    user_id TEXT PRIMARY KEY,
    hypothesis TEXT DEFAULT '',
    phase TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS judgment (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
