import sqlite3
import json
import time

DB = "data.db"

def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, name TEXT, username TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS demos (
            id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS pending (
            user_id INTEGER PRIMARY KEY, photo_id TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT)""")
        c.execute("""CREATE TABLE IF NOT EXISTS history (
            key TEXT PRIMARY KEY, val INTEGER DEFAULT 0)""")
        c.execute("""CREATE TABLE IF NOT EXISTS states (
            user_id INTEGER PRIMARY KEY, state TEXT)""")
        # Per-admin notification preferences
        c.execute("""CREATE TABLE IF NOT EXISTS admin_prefs (
            admin_id INTEGER PRIMARY KEY,
            new_user_notify INTEGER DEFAULT 1)""")
        c.commit()

    defaults = {
        "upi":            "example@ybl",
        "support":        "@nglynx",
        "premium_image":  "https://i.ibb.co/9x38myC/x.jpg",
        "price_indian":   "59",
        "price_premium":  "99",
        "price_movies":   "149",
        "price_all":      "249",
        "link_indian":    "https://t.me/link1",
        "link_premium":   "https://t.me/link2",
        "link_movies":    "https://t.me/link3",
        "link_all":       "https://t.me/link4",
        "how_to_video":   "",
        "proof_link":     "",
        "extra_admins":   "",
    }
    with conn() as c:
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO settings (key,value) VALUES (?,?)", (k, v))
        c.execute("INSERT OR IGNORE INTO history (key,val) VALUES ('approved',0)")
        c.execute("INSERT OR IGNORE INTO history (key,val) VALUES ('rejected',0)")
        c.commit()

init()

# ── settings ────────────────────────────────────────────────
def get_setting(key):
    with conn() as c:
        r = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return r["value"] if r else ""

def set_setting(key, value):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO settings (key,value) VALUES (?,?)", (key, str(value)))
        c.commit()

def all_settings():
    with conn() as c:
        rows = c.execute("SELECT key,value FROM settings").fetchall()
    return {r["key"]: r["value"] for r in rows}

# ── users ────────────────────────────────────────────────────
def add_user(uid, name, username):
    """Returns True if NEW user (just inserted), False if existing."""
    with conn() as c:
        existing = c.execute("SELECT user_id FROM users WHERE user_id=?", (uid,)).fetchone()
        is_new = existing is None
        c.execute("INSERT OR REPLACE INTO users (user_id,name,username) VALUES (?,?,?)",
                  (uid, name, username))
        c.commit()
    return is_new

def get_all_users():
    with conn() as c:
        return [r["user_id"] for r in c.execute("SELECT user_id FROM users").fetchall()]

def get_user_details():
    with conn() as c:
        return c.execute("SELECT user_id,name,username FROM users").fetchall()

def total_users():
    with conn() as c:
        return c.execute("SELECT COUNT(*) as n FROM users").fetchone()["n"]

# ── states ───────────────────────────────────────────────────
def get_state(uid):
    with conn() as c:
        r = c.execute("SELECT state FROM states WHERE user_id=?", (uid,)).fetchone()
    return r["state"] if r else "none"

def set_state(uid, state):
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO states (user_id,state) VALUES (?,?)", (uid, state))
        c.commit()

# ── demos ────────────────────────────────────────────────────
def get_demos():
    with conn() as c:
        return [(r["id"], r["file_id"]) for r in c.execute("SELECT id,file_id FROM demos").fetchall()]

def add_demo(file_id):
    with conn() as c:
        c.execute("INSERT INTO demos (file_id) VALUES (?)", (file_id,))
        c.commit()

def del_demo(demo_id):
    with conn() as c:
        c.execute("DELETE FROM demos WHERE id=?", (demo_id,))
        c.commit()

# ── history ──────────────────────────────────────────────────
def get_history():
    with conn() as c:
        rows = c.execute("SELECT key,val FROM history").fetchall()
    return {r["key"]: r["val"] for r in rows}

def inc_history(key):
    with conn() as c:
        c.execute("UPDATE history SET val=val+1 WHERE key=?", (key,))
        c.commit()

# ── admin notification prefs ─────────────────────────────────
def get_admin_notify(admin_id):
    """Returns True if this admin wants new user notifications (default: ON)."""
    with conn() as c:
        r = c.execute("SELECT new_user_notify FROM admin_prefs WHERE admin_id=?", (admin_id,)).fetchone()
    return (r["new_user_notify"] == 1) if r else True

def set_admin_notify(admin_id, enabled: bool):
    with conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO admin_prefs (admin_id, new_user_notify) VALUES (?,?)",
            (admin_id, 1 if enabled else 0)
        )
        c.commit()
