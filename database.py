import sqlite3
import datetime
from typing import Dict, List, Optional
from config import DATASET_DB

# Corrected topics table (previous version had missing commas and misordered columns)
TOPICS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS topics (
    scraped_at_unix INTEGER,
    topic_id INTEGER PRIMARY KEY,
    slug TEXT,
    url TEXT,
    title TEXT,
    created_at_unix INTEGER
)
"""

# Posts table now includes a foreign key referencing topics(topic_id)
POSTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS posts (
    scraped_at_unix INTEGER,
    post_id INTEGER PRIMARY KEY,
    topic_id INTEGER NOT NULL,
    post_number INTEGER,
    url TEXT,
    username TEXT,
    display_name TEXT,
    created_at_unix INTEGER,
    body TEXT,
    FOREIGN KEY (topic_id) REFERENCES topics(topic_id) ON DELETE CASCADE
)
"""

TABLE_DEFINITIONS: List[str] = [TOPICS_TABLE_SQL, POSTS_TABLE_SQL]

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DATASET_DB)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def write(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    for ddl in TABLE_DEFINITIONS:
        cursor.execute(ddl)
    connection.commit()

def ensure_posts_foreign_key(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA foreign_key_list(posts)")
    fk_rows = cursor.fetchall()
    has_fk = any(row[3] == "topic_id" for row in fk_rows)
    if not has_fk:
        # Rebuild posts table preserving data
        cursor.execute("ALTER TABLE posts RENAME TO posts_old")
        cursor.execute(POSTS_TABLE_SQL)
        cursor.execute(
            """
            INSERT INTO posts (post_id, topic_id, post_number, username, display_name, created_at_unix, body, url, scraped_at_unix)
            SELECT post_id, topic_id, post_number, username, display_name, created_at_unix, body, url, scraped_at_unix FROM posts_old
            """
        )
        cursor.execute("DROP TABLE posts_old")
        connection.commit()

def ensure_schema(connection: sqlite3.Connection) -> None:
    cursor = connection.cursor()
    cursor.execute("PRAGMA table_info(posts)")
    cols = {row[1] for row in cursor.fetchall()}
    if "created_at_unix" not in cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN created_at_unix INTEGER")
    if "scraped_at_unix" not in cols:
        cursor.execute("ALTER TABLE posts ADD COLUMN scraped_at_unix INTEGER")

    cursor.execute("PRAGMA table_info(topics)")
    topic_cols = {row[1] for row in cursor.fetchall()}
    if topic_cols:
        if "created_at_unix" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN created_at_unix INTEGER")
        if "scraped_at_unix" not in topic_cols:
            cursor.execute("ALTER TABLE topics ADD COLUMN scraped_at_unix INTEGER")
    connection.commit()
    ensure_posts_foreign_key(connection)

def parse_iso8601_to_dt(s: Optional[str]) -> Optional[datetime.datetime]:
    if not s:
        return None
    try:
        ss = s.replace("Z", "+00:00")
        dt = datetime.datetime.fromisoformat(ss)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        return dt
    except Exception:
        return None

def save_posts(posts: List[Dict]) -> int:
    connection = get_connection()
    write(connection)
    ensure_schema(connection)
    cursor = connection.cursor()
    inserted = 0
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_unix = int(now_dt.timestamp())
    for p in posts:
        created_at_dt = parse_iso8601_to_dt(p.get("created_at"))
        created_at_unix = int(created_at_dt.timestamp()) if created_at_dt else None
        # NOTE: Table column names (display_name/body) differ from scraped keys (name/cooked).
        # Mapping is done inline here. Adjust if upstream keys change.
        cursor.execute(
            """
            INSERT OR REPLACE INTO posts (
                scraped_at_unix,
                post_id,
                topic_id,
                post_number,
                url,
                username,
                display_name,
                created_at_unix,
                body
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                now_unix,
                p.get("post_id"),
                p.get("topic_id"),
                p.get("post_number"),
                p.get("url"),
                p.get("username"),
                p.get("name"),
                created_at_unix,
                p.get("cooked"),
            ),
        )
        inserted += 1
    connection.commit()
    connection.close()
    return inserted

def save_topic(topic: Dict) -> int:
    connection = get_connection()
    write(connection)
    ensure_schema(connection)
    cursor = connection.cursor()
    created_at_dt = parse_iso8601_to_dt(topic.get("created_at"))
    created_at_unix = int(created_at_dt.timestamp()) if created_at_dt else None
    now_unix = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    cursor.execute(
        """
        INSERT OR REPLACE INTO topics (
            scraped_at_unix,
            topic_id,
            slug,
            url,
            title,
            created_at_unix
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            now_unix,
            topic.get("topic_id"),
            topic.get("slug"),
            topic.get("url"),
            topic.get("title"),
            created_at_unix,
        ),
    )
    connection.commit()
    connection.close()
    return 1
