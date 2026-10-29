import os
import sqlite3
from datetime import datetime
from database import connect
import sys

# Get the absolute path for cloud_storage folder - use user home directory for persistence
if getattr(sys, 'frozen', False):
    # Running as executable - use home directory
    BASE_DIR = os.path.expanduser("~")
    APP_DATA_DIR = os.path.join(BASE_DIR, "Velora Cloud")
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    APP_DATA_DIR = BASE_DIR

os.makedirs(APP_DATA_DIR, exist_ok=True)
MAIN_FOLDER = os.path.join(APP_DATA_DIR, "cloud_storage")
os.makedirs(MAIN_FOLDER, exist_ok=True)


def _normalize_storage_path(path):
    return os.path.normpath(path).replace("\\", "/").strip("/")


def _upsert_folder(cursor, folder_path, user_id, group_id):
    normalized_folder = _normalize_storage_path(folder_path)
    if not normalized_folder:
        return

    try:
        cursor.execute(
            """
            INSERT INTO folders (folder_path, owner_id, group_id, date_created, is_deleted)
            VALUES (?, ?, ?, ?, 0)
            """,
            (normalized_folder, user_id, group_id, datetime.now().isoformat())
        )
    except sqlite3.IntegrityError:
        cursor.execute(
            """
            UPDATE folders
            SET is_deleted = 0
            WHERE folder_path = ? AND group_id = ?
            """,
            (normalized_folder, group_id)
        )


def _upsert_folder_hierarchy(cursor, path, user_id, group_id):
    normalized_path = _normalize_storage_path(path)
    if not normalized_path:
        return

    parts = normalized_path.split("/")
    current = ""
    for part in parts:
        current = f"{current}/{part}" if current else part
        _upsert_folder(cursor, current, user_id, group_id)


def save_folder(folder_path, user_id, group_id):
    """Persist a folder path so empty folders are visible in UI."""
    normalized_folder = _normalize_storage_path(folder_path)
    if not normalized_folder:
        return

    conn = connect()
    cursor = conn.cursor()
    try:
        _upsert_folder_hierarchy(cursor, normalized_folder, user_id, group_id)
        conn.commit()
    finally:
        conn.close()


def get_group_folders(group_id):
    """Get all active folders for a group."""
    conn = connect()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT folder_path, date_created, owner_id
        FROM folders
        WHERE group_id = ? AND is_deleted = 0
        ORDER BY folder_path COLLATE NOCASE ASC
        """,
        (group_id,)
    )
    folders = cursor.fetchall()
    conn.close()
    return folders

def save_file(filename, user_id, group_id, content=None):
    """Save file to storage and database"""
    normalized_filename = _normalize_storage_path(filename)
    file_path = os.path.join(MAIN_FOLDER, normalized_filename)
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)
    file_size = 0

    if content is None:
        payload = "Sample File Content"
    elif isinstance(content, (bytes, bytearray)):
        payload = bytes(content)
    else:
        payload = str(content)

    # Write file content
    if isinstance(payload, bytes):
        with open(file_path, "wb") as file_handle:
            file_handle.write(payload)
        file_size = len(payload)
    else:
        with open(file_path, "w", encoding="utf-8") as file_handle:
            file_handle.write(payload)
        file_size = len(payload.encode("utf-8"))
    
    # Determine file type
    file_extension = os.path.splitext(filename)[1].lower()
    file_type = file_extension[1:] if file_extension else "unknown"

    conn = connect()
    cursor = conn.cursor()

    try:
        folder_path = os.path.dirname(normalized_filename)
        if folder_path:
            _upsert_folder_hierarchy(cursor, folder_path, user_id, group_id)

        cursor.execute("""
        INSERT INTO files (filename, original_name, file_size, file_type, owner_id, group_id, date_uploaded, last_modified)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (normalized_filename, normalized_filename, file_size, file_type, user_id, group_id, datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        
    except sqlite3.IntegrityError:
        # File already exists, update it
        cursor.execute("""
            UPDATE files 
            SET file_size=?, last_modified=?, is_deleted=0 
            WHERE filename=? AND group_id=?
        """, (file_size, datetime.now().isoformat(), normalized_filename, group_id))
        conn.commit()
    finally:
        conn.close()

def get_group_files(group_id):
    """Get all active files for a group"""
    conn = connect()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT filename, file_size, file_type, date_uploaded, owner_id 
        FROM files 
        WHERE group_id=? AND is_deleted=0
        ORDER BY date_uploaded DESC
    """, (group_id,))
    files = cursor.fetchall()

    conn.close()
    return files

def get_file_info(filename, group_id):
    """Get detailed information about a file"""
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT f.date_uploaded, u.username, f.file_size, f.file_type, f.download_count
        FROM files f
        JOIN users u ON f.owner_id = u.id
        WHERE f.filename = ? AND f.group_id = ? AND f.is_deleted = 0
    """, (filename, group_id))
    
    result = cursor.fetchone()
    conn.close()
    
    if result:
        date_str = result[0].split('.')[0] if '.' in str(result[0]) else str(result[0])
        size_kb = result[2] / 1024 if result[2] else 0
        
        return {
            'date': date_str[:16] if len(date_str) > 16 else date_str,
            'owner': result[1],
            'size': f"{size_kb:.2f} KB" if size_kb < 1024 else f"{size_kb/1024:.2f} MB",
            'type': result[3],
            'downloads': result[4]
        }
    return None

def download_file(filename, group_id):
    """Retrieve file content for download"""
    normalized_filename = _normalize_storage_path(filename)
    file_path = os.path.join(MAIN_FOLDER, normalized_filename)
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File '{filename}' not found in storage")
    
    # Verify file belongs to group
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files WHERE filename=? AND group_id=? AND is_deleted=0", (normalized_filename, group_id))
    file_info = cursor.fetchone()
    conn.close()
    
    if not file_info:
        raise PermissionError(f"File '{filename}' not found in your group storage")
    
    return file_path

def delete_file_from_storage(filename, group_id, user_id=None):
    """Mark file as deleted in database and remove physical file"""
    normalized_filename = _normalize_storage_path(filename)
    conn = connect()
    cursor = conn.cursor()
    
    # Get file info before deletion
    cursor.execute("SELECT id, owner_id FROM files WHERE filename=? AND group_id=?", (normalized_filename, group_id))
    file_info = cursor.fetchone()
    
    if file_info:
        # Soft delete in database
        cursor.execute("""
            UPDATE files 
            SET is_deleted=1, last_modified=?
            WHERE filename=? AND group_id=?
        """, (datetime.now().isoformat(), normalized_filename, group_id))
        conn.commit()
        
        # Delete physical file
        file_path = os.path.join(MAIN_FOLDER, normalized_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    
    conn.close()
