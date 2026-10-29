import sqlite3
from datetime import datetime
from contextlib import contextmanager
import sys
import os

# Get the absolute path for database - use user home directory for persistence
if getattr(sys, 'frozen', False):
    # Running as executable - use home directory
    BASE_DIR = os.path.expanduser("~")
    APP_DATA_DIR = os.path.join(BASE_DIR, "Velora Cloud")
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DATA_DIR = BASE_DIR

os.makedirs(APP_DATA_DIR, exist_ok=True)
DATABASE_NAME = os.path.join(APP_DATA_DIR, "lovera.db")

@contextmanager
def get_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row  # Enable column access by name
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def connect():
    """Simple connection function for backward compatibility"""
    return sqlite3.connect(DATABASE_NAME)

def create_tables():
    """Create all database tables with proper constraints and indexes"""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Users table with constraints
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('admin', 'user', 'moderator')),
            group_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_login TEXT,
            is_active INTEGER DEFAULT 1,
            CONSTRAINT fk_group FOREIGN KEY (group_id) REFERENCES groups(id)
        )
        """)

        # Groups table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            description TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            max_storage_mb INTEGER DEFAULT 1000
        )
        """)

        # Files table with enhanced metadata
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_name TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            owner_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            date_uploaded TEXT DEFAULT CURRENT_TIMESTAMP,
            last_modified TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            download_count INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            UNIQUE(filename, group_id)
        )
        """)

        # Folders table to preserve empty directories
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS folders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            folder_path TEXT NOT NULL,
            owner_id INTEGER NOT NULL,
            group_id INTEGER NOT NULL,
            date_created TEXT DEFAULT CURRENT_TIMESTAMP,
            is_deleted INTEGER DEFAULT 0,
            FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
            UNIQUE(folder_path, group_id)
        )
        """)

        # File shares table for sharing between users
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS file_shares (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id INTEGER NOT NULL,
            shared_by INTEGER NOT NULL,
            shared_with INTEGER NOT NULL,
            permission TEXT CHECK(permission IN ('read', 'write', 'delete')),
            shared_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_by) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (shared_with) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # Activity logs table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id INTEGER,
            details TEXT,
            ip_address TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """)

        # Create indexes for better query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_group ON users(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_owner ON files(owner_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_group ON files(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_uploaded ON files(date_uploaded)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folders_group ON folders(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_user ON logs(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_logs_timestamp ON logs(timestamp)")
        
        # Insert default group if not exists
        cursor.execute("SELECT COUNT(*) FROM groups")
        if cursor.fetchone()[0] == 0:
            cursor.execute("""
                INSERT INTO groups (id, name, description, max_storage_mb)
                VALUES (1, 'Default Group', 'Default group for all users', 5000)
            """)

def log_activity(user_id, action, resource_type=None, resource_id=None, details=None):
    """Log user activity to the logs table"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO logs (user_id, action, resource_type, resource_id, details, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, action, resource_type, resource_id, details, datetime.now().isoformat()))

def get_user_by_id(user_id):
    """Get user information by ID"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

def get_user_by_username(username):
    """Get user information by username"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        return cursor.fetchone()

def update_last_login(user_id):
    """Update user's last login timestamp"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users SET last_login = ? WHERE id = ?
        """, (datetime.now().isoformat(), user_id))

def get_group_info(group_id):
    """Get group information"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM groups WHERE id = ?", (group_id,))
        return cursor.fetchone()

def get_storage_usage(group_id):
    """Calculate total storage used by a group in MB"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(SUM(file_size), 0) as total_bytes
            FROM files 
            WHERE group_id = ? AND is_deleted = 0
        """, (group_id,))
        result = cursor.fetchone()
        return result[0] / (1024 * 1024) if result[0] else 0  # Convert to MB

def get_user_file_count(user_id):
    """Get total number of files uploaded by user"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM files 
            WHERE owner_id = ? AND is_deleted = 0
        """, (user_id,))
        return cursor.fetchone()[0]

def get_recent_activities(user_id, limit=10):
    """Get recent activities for a user"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT action, resource_type, details, timestamp
            FROM logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()

def cleanup_old_logs(days=90):
    """Delete logs older than specified days"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cutoff_date = datetime.now().replace(day=datetime.now().day - days)
        cursor.execute("""
            DELETE FROM logs WHERE timestamp < ?
        """, (cutoff_date.isoformat(),))
        return cursor.rowcount

def get_database_stats():
    """Get overall database statistics"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        stats = {}
        
        # Total users
        cursor.execute("SELECT COUNT(*) FROM users WHERE is_active = 1")
        stats['total_users'] = cursor.fetchone()[0]
        
        # Total files
        cursor.execute("SELECT COUNT(*) FROM files WHERE is_deleted = 0")
        stats['total_files'] = cursor.fetchone()[0]
        
        # Total groups
        cursor.execute("SELECT COUNT(*) FROM groups")
        stats['total_groups'] = cursor.fetchone()[0]
        
        # Total storage (MB)
        cursor.execute("SELECT COALESCE(SUM(file_size), 0) FROM files WHERE is_deleted = 0")
        stats['total_storage_mb'] = cursor.fetchone()[0] / (1024 * 1024)
        
        # Recent activity count (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) FROM logs 
            WHERE timestamp > datetime('now', '-1 day')
        """)
        stats['recent_activities'] = cursor.fetchone()[0]
        
        return stats
