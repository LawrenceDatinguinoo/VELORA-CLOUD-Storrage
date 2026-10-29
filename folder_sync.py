import json
import os
import threading
import time

from storage import APP_DATA_DIR, save_file, save_folder

SYNC_CONFIG_PATH = os.path.join(APP_DATA_DIR, "sync_config.json")


def _config_key(user_id, group_id):
    return f"{user_id}:{group_id}"


def _normalize_folder_path(folder_path):
    return os.path.abspath(folder_path) if folder_path else None


def load_user_sync_folders(user_id, group_id):
    if not os.path.exists(SYNC_CONFIG_PATH):
        return []

    try:
        with open(SYNC_CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except Exception:
        return []

    value = data.get(_config_key(user_id, group_id))
    if isinstance(value, str):
        normalized = _normalize_folder_path(value)
        return [normalized] if normalized else []

    if isinstance(value, list):
        normalized_folders = []
        for folder_path in value:
            if not isinstance(folder_path, str):
                continue
            normalized = _normalize_folder_path(folder_path)
            if normalized and normalized not in normalized_folders:
                normalized_folders.append(normalized)
        return normalized_folders

    return []


def load_all_sync_mappings():
    """Load all user/group sync folder mappings from config.

    Returns:
        dict[tuple[int, int], list[str]]: {(user_id, group_id): [folder_path, ...]}
    """
    if not os.path.exists(SYNC_CONFIG_PATH):
        return {}

    try:
        with open(SYNC_CONFIG_PATH, "r", encoding="utf-8") as config_file:
            data = json.load(config_file)
    except Exception:
        return {}

    mappings = {}
    for key, value in data.items():
        if not isinstance(key, str) or ":" not in key:
            continue

        user_text, group_text = key.split(":", 1)
        try:
            user_id = int(user_text)
            group_id = int(group_text)
        except ValueError:
            continue

        folder_list = []
        if isinstance(value, str):
            normalized = _normalize_folder_path(value)
            if normalized:
                folder_list = [normalized]
        elif isinstance(value, list):
            for folder_path in value:
                if not isinstance(folder_path, str):
                    continue
                normalized = _normalize_folder_path(folder_path)
                if normalized and normalized not in folder_list:
                    folder_list.append(normalized)

        if folder_list:
            mappings[(user_id, group_id)] = folder_list

    return mappings


def load_user_sync_folder(user_id, group_id):
    folders = load_user_sync_folders(user_id, group_id)
    return folders[0] if folders else None


def save_user_sync_folders(user_id, group_id, folder_paths):
    data = {}

    if os.path.exists(SYNC_CONFIG_PATH):
        try:
            with open(SYNC_CONFIG_PATH, "r", encoding="utf-8") as config_file:
                data = json.load(config_file)
        except Exception:
            data = {}

    normalized_folders = []
    for folder_path in folder_paths:
        normalized = _normalize_folder_path(folder_path)
        if normalized and normalized not in normalized_folders:
            normalized_folders.append(normalized)

    data[_config_key(user_id, group_id)] = normalized_folders

    with open(SYNC_CONFIG_PATH, "w", encoding="utf-8") as config_file:
        json.dump(data, config_file, indent=2)

def save_user_sync_folder(user_id, group_id, folder_path):
    normalized = _normalize_folder_path(folder_path)
    if not normalized:
        return

    existing_folders = load_user_sync_folders(user_id, group_id)
    if normalized not in existing_folders:
        existing_folders.append(normalized)
    save_user_sync_folders(user_id, group_id, existing_folders)


class FolderSyncService:
    def __init__(self, user_id, group_id, on_sync=None, on_error=None, poll_interval=1):
        self.user_id = user_id
        self.group_id = group_id
        self.on_sync = on_sync
        self.on_error = on_error
        self.poll_interval = poll_interval

        self.folder_path = None
        self.folder_alias = None
        self._known_files = {}
        self._stop_event = threading.Event()
        self._thread = None

    def set_folder(self, folder_path):
        if not folder_path:
            raise ValueError("Folder path is required")

        absolute_path = os.path.abspath(folder_path)
        if not os.path.isdir(absolute_path):
            raise FileNotFoundError("Selected folder does not exist")

        self.folder_path = absolute_path
        self.folder_alias = os.path.basename(absolute_path.rstrip("\\/")) or "SyncedFolder"
        save_folder(self.folder_alias, self.user_id, self.group_id)
        self._known_files = {}

    def start(self):
        if not self.folder_path:
            return

        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _run(self):
        while not self._stop_event.is_set():
            try:
                self._sync_once()
            except Exception as error:
                if self.on_error:
                    self.on_error(str(error))
            time.sleep(self.poll_interval)

    def _snapshot_folder(self):
        snapshot = {}

        if not self.folder_path or not os.path.isdir(self.folder_path):
            return snapshot

        for root, _, files in os.walk(self.folder_path):
            for name in files:
                full_path = os.path.join(root, name)
                relative_path = os.path.relpath(full_path, self.folder_path).replace("\\", "/")
                try:
                    stats = os.stat(full_path)
                    snapshot[relative_path] = (stats.st_mtime_ns, stats.st_size)
                except OSError:
                    continue

        return snapshot

    def _sync_once(self):
        if not self.folder_path or not os.path.isdir(self.folder_path):
            return

        for root, dirs, _ in os.walk(self.folder_path):
            relative_root = os.path.relpath(root, self.folder_path).replace("\\", "/")
            if relative_root == ".":
                current_cloud_root = self.folder_alias
            else:
                current_cloud_root = f"{self.folder_alias}/{relative_root}" if self.folder_alias else relative_root

            save_folder(current_cloud_root, self.user_id, self.group_id)

            for directory_name in dirs:
                subfolder_path = f"{current_cloud_root}/{directory_name}" if current_cloud_root else directory_name
                save_folder(subfolder_path, self.user_id, self.group_id)

        current_snapshot = self._snapshot_folder()

        for filename, file_state in current_snapshot.items():
            previous_state = self._known_files.get(filename)
            if previous_state == file_state:
                continue

            try:
                full_path = os.path.join(self.folder_path, filename)
                with open(full_path, "rb") as source_file:
                    content = source_file.read()

                cloud_filename = f"{self.folder_alias}/{filename}" if self.folder_alias else filename
                save_file(cloud_filename, self.user_id, self.group_id, content)

                if self.on_sync:
                    action = "added" if previous_state is None else "updated"
                    self.on_sync(filename, action)
            except Exception as file_error:
                if self.on_error:
                    self.on_error(f"{filename}: {file_error}")
                continue

        self._known_files = current_snapshot