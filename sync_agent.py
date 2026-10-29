import os
import signal
import threading
import time
from datetime import datetime

from folder_sync import FolderSyncService, load_all_sync_mappings


class BackgroundSyncAgent:
    def __init__(self, poll_interval=1, reload_interval=5):
        self.poll_interval = poll_interval
        self.reload_interval = reload_interval
        self.services = {}
        self._stop_event = threading.Event()

    def _log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {message}", flush=True)

    def _on_sync(self, user_id, group_id, folder_path):
        def callback(filename, action):
            self._log(f"Synced ({user_id}:{group_id}) [{os.path.basename(folder_path)}] {action}: {filename}")

        return callback

    def _on_error(self, user_id, group_id, folder_path):
        def callback(error_message):
            self._log(f"Sync error ({user_id}:{group_id}) [{folder_path}]: {error_message}")

        return callback

    def _desired_targets(self):
        mappings = load_all_sync_mappings()
        desired = set()

        for (user_id, group_id), folder_paths in mappings.items():
            for folder_path in folder_paths:
                normalized = os.path.abspath(folder_path)
                if os.path.isdir(normalized):
                    desired.add((user_id, group_id, normalized))

        return desired

    def _start_service(self, user_id, group_id, folder_path):
        service = FolderSyncService(
            user_id=user_id,
            group_id=group_id,
            on_sync=self._on_sync(user_id, group_id, folder_path),
            on_error=self._on_error(user_id, group_id, folder_path),
            poll_interval=self.poll_interval,
        )
        service.set_folder(folder_path)
        service.start()
        self.services[(user_id, group_id, folder_path)] = service
        self._log(f"Watching ({user_id}:{group_id}) {folder_path}")

    def _stop_service(self, key):
        service = self.services.pop(key, None)
        if service:
            service.stop()
            user_id, group_id, folder_path = key
            self._log(f"Stopped ({user_id}:{group_id}) {folder_path}")

    def reconcile(self):
        desired = self._desired_targets()
        current = set(self.services.keys())

        for key in current - desired:
            self._stop_service(key)

        for key in desired - current:
            user_id, group_id, folder_path = key
            try:
                self._start_service(user_id, group_id, folder_path)
            except Exception as error:
                self._log(f"Failed to watch ({user_id}:{group_id}) {folder_path}: {error}")

    def stop(self):
        self._stop_event.set()

    def run_forever(self):
        self._log("Background sync agent started")
        try:
            while not self._stop_event.is_set():
                self.reconcile()
                time.sleep(self.reload_interval)
        finally:
            for key in list(self.services.keys()):
                self._stop_service(key)
            self._log("Background sync agent stopped")


def main():
    agent = BackgroundSyncAgent(poll_interval=1, reload_interval=5)

    def handle_stop(*_):
        agent.stop()

    signal.signal(signal.SIGINT, handle_stop)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_stop)

    agent.run_forever()


if __name__ == "__main__":
    main()
