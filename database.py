import psycopg2
import psycopg2.extras
import os

DB_URL = os.environ.get('DATABASE_URL', '')


def get_db():
    conn = psycopg2.connect(DB_URL)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            deliver_at TIMESTAMP DEFAULT NOW(),
            msg_type TEXT DEFAULT 'response'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS state (
            user_id TEXT PRIMARY KEY,
            hypothesis TEXT DEFAULT '',
            phase TEXT DEFAULT 'active'
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS judgment (
            id SERIAL PRIMARY KEY,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
    """)
    cur.execute("ALTER TABLE messages ADD COLUMN IF NOT EXISTS msg_type TEXT DEFAULT 'response'")
    for uid in ('ruth', 'shakti'):
        cur.execute("INSERT INTO state (user_id) VALUES (%s) ON CONFLICT DO NOTHING", (uid,))
    conn.commit()
    cur.close()
    conn.close()


def add_message(user_id, role, content, msg_type='response', deliver_at=None):
    conn = get_db()
    cur = conn.cursor()
    if deliver_at:
        cur.execute(
            "INSERT INTO messages (user_id, role, content, msg_type, deliver_at) VALUES (%s, %s, %s, %s, %s)",
            (user_id, role, content, msg_type, deliver_at)
        )
    else:
        cur.execute(
            "INSERT INTO messages (user_id, role, content, msg_type) VALUES (%s, %s, %s, %s)",
            (user_id, role, content, msg_type)
        )
    conn.commit()
    cur.close()
    conn.close()


def get_all_messages(user_id):
    """All messages regardless of deliver_at — used by bot for reasoning."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, role, content, created_at, deliver_at FROM messages "
        "WHERE user_id = %s ORDER BY id ASC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_visible_messages(user_id):
    """Only messages where deliver_at <= now — shown to the user."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, role, content, created_at, deliver_at, msg_type FROM messages "
        "WHERE user_id = %s AND deliver_at <= NOW() ORDER BY deliver_at ASC, id ASC",
        (user_id,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def count_bot_responses(user_id):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM messages WHERE user_id = %s AND role = 'bot' AND msg_type = 'response'",
        (user_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count


def get_last_bot_message(user_id):
    """Returns the last bot message row (including msg_type), or None."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT content, created_at, msg_type FROM messages "
        "WHERE user_id = %s AND role = 'bot' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def get_last_bot_message_time(user_id):
    """Returns created_at of the last substantive (non-ack) bot message as a string, or None."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT created_at FROM messages "
        "WHERE user_id = %s AND role = 'bot' AND msg_type = 'response' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and row[0]:
        return row[0].strftime('%Y-%m-%d %H:%M:%S')
    return None


def has_pending_bot_message(user_id):
    """Returns True if there's a bot response generated but not yet delivered."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM messages WHERE user_id = %s AND role = 'bot' AND deliver_at > NOW()",
        (user_id,)
    )
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count > 0


def get_messages_since_last_bot(user_id):
    """User messages sent after the last substantive (non-ack) bot message."""
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id FROM messages "
        "WHERE user_id = %s AND role = 'bot' AND msg_type = 'response' ORDER BY id DESC LIMIT 1",
        (user_id,)
    )
    last_bot = cur.fetchone()
    if last_bot:
        cur.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE user_id = %s AND role = 'user' AND id > %s ORDER BY id ASC",
            (user_id, last_bot['id'])
        )
    else:
        cur.execute(
            "SELECT id, role, content, created_at FROM messages "
            "WHERE user_id = %s AND role = 'user' ORDER BY id ASC",
            (user_id,)
        )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(r) for r in rows]


def get_state(user_id):
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM state WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else {}


def set_hypothesis(hypothesis):
    conn = get_db()
    cur = conn.cursor()
    for uid in ('ruth', 'shakti'):
        cur.execute("UPDATE state SET hypothesis = %s WHERE user_id = %s", (hypothesis, uid))
    conn.commit()
    cur.close()
    conn.close()


def set_phase(user_id, phase):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE state SET phase = %s WHERE user_id = %s", (phase, user_id))
    conn.commit()
    cur.close()
    conn.close()


def save_judgment(content):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO judgment (content) VALUES (%s)", (content,))
    conn.commit()
    cur.close()
    conn.close()


def get_latest_judgment():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM judgment ORDER BY id DESC LIMIT 1")
    row = cur.fetchone()
    cur.close()
    conn.close()
    return dict(row) if row else None


def accelerate_pending():
    """Move all future deliver_at timestamps to now. For demos."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE messages SET deliver_at = NOW() WHERE deliver_at > NOW()")
    conn.commit()
    cur.close()
    conn.close()


def reset_all():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages")
    cur.execute("DELETE FROM state")
    cur.execute("DELETE FROM judgment")
    conn.commit()
    cur.close()
    conn.close()
    init_db()
