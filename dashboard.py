import customtkinter as ctk
from storage import get_group_files, get_group_folders, save_file, save_folder, delete_file_from_storage, get_file_info, download_file
from folder_sync import FolderSyncService, load_user_sync_folders, save_user_sync_folder
from tkinter import filedialog, messagebox
import os

# Velora Cloud Theme Colors (from logo)
VELORA_ROYAL_BLUE = "#4169E1"
VELORA_DARK_BLUE = "#1E1E4D"
VELORA_NAVY = "#2B2B5E"
VELORA_PURPLE = "#5C4DB8"
VELORA_GRAY = "#808080"
VELORA_LIGHT_GRAY = "#A9A9A9"
VELORA_DARK_BG = "#0D0D1E"
VELORA_CARD_BG = "#1A1A3E"
VELORA_ACCENT = "#6B5CE0"
VELORA_CLOUD_GRAY = "#B0B0B0"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class Dashboard(ctk.CTk):
    def __init__(self, user):
        super().__init__()

        self.user = user
        self.title("☁️ Velora Cloud Dashboard")
        self.geometry("1200x750")
        self.selected_file = None
        self.current_folder = ""
        self._refresh_job = None
        self.sync_folder_path = None
        self.sync_services = {}
        self._auto_discovering_sync = False
        self.configure(fg_color=VELORA_DARK_BG)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Configure grid
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0, fg_color=VELORA_NAVY)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        
        # Logo Area - Text only
        logo_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_container.pack(pady=(40, 5))
        
        # Velora text - centered and prominent
        ctk.CTkLabel(
            logo_container,
            text="VELORA",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color=VELORA_ROYAL_BLUE
        ).pack(pady=(0, 5))
        
        # Checkmark with Cloud text
        checkmark_frame = ctk.CTkFrame(logo_container, fg_color="transparent")
        checkmark_frame.pack(pady=(0, 20))
        
        ctk.CTkLabel(
            checkmark_frame,
            text="✓",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#000000"
        ).pack(side="left", padx=3)
        
        ctk.CTkLabel(
            checkmark_frame,
            text="CLOUD",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=VELORA_ROYAL_BLUE
        ).pack(side="left")
        
        # User Info Card
        user_card = ctk.CTkFrame(self.sidebar, fg_color=VELORA_CARD_BG, corner_radius=10)
        user_card.pack(padx=15, pady=20, fill="x")
        
        ctk.CTkLabel(
            user_card,
            text="✓ User Profile",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=VELORA_LIGHT_GRAY
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        ctk.CTkLabel(
            user_card,
            text=f"{user[1]}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=VELORA_ROYAL_BLUE
        ).pack(anchor="w", padx=15, pady=2)
        
        ctk.CTkLabel(
            user_card,
            text=f"Role: {user[3].upper()}",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY
        ).pack(anchor="w", padx=15, pady=2)
        
        ctk.CTkLabel(
            user_card,
            text=f"Group ID: {user[4]}",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY
        ).pack(anchor="w", padx=15, pady=(2, 10))
        
        # Menu buttons
        ctk.CTkLabel(
            self.sidebar,
            text="MENU",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=VELORA_GRAY
        ).pack(anchor="w", padx=20, pady=(20, 10))
        
        self.files_btn = ctk.CTkButton(
            self.sidebar,
            text="☁️ My Files",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            corner_radius=8,
            fg_color=VELORA_ROYAL_BLUE,
            hover_color=VELORA_PURPLE,
            anchor="w",
            command=self.show_root_files
        )
        self.files_btn.pack(padx=15, pady=5, fill="x")
        
        self.upload_btn = ctk.CTkButton(
            self.sidebar,
            text="☁️ ↑ Upload File",
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            border_color=VELORA_ROYAL_BLUE,
            text_color=VELORA_ROYAL_BLUE,
            anchor="w",
            hover_color=VELORA_CARD_BG,
            command=self.upload_file
        )
        self.upload_btn.pack(padx=15, pady=5, fill="x")

        self.upload_folder_btn = ctk.CTkButton(
            self.sidebar,
            text="📁 ↑ Upload Folder",
            font=ctk.CTkFont(size=14),
            height=40,
            corner_radius=8,
            fg_color="transparent",
            border_width=2,
            border_color=VELORA_ROYAL_BLUE,
            text_color=VELORA_ROYAL_BLUE,
            anchor="w",
            hover_color=VELORA_CARD_BG,
            command=self.upload_folder
        )
        self.upload_folder_btn.pack(padx=15, pady=5, fill="x")

        # Sync folder controls
        sync_frame = ctk.CTkFrame(self.sidebar, fg_color=VELORA_CARD_BG, corner_radius=10)
        sync_frame.pack(padx=15, pady=15, fill="x")

        ctk.CTkLabel(
            sync_frame,
            text="📁 Auto-Sync Folder",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=VELORA_LIGHT_GRAY
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.sync_folder_label = ctk.CTkLabel(
            sync_frame,
            text="Not set",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY,
            anchor="w",
            justify="left"
        )
        self.sync_folder_label.pack(anchor="w", padx=15, pady=(0, 8))

        self.sync_btn = ctk.CTkButton(
            sync_frame,
            text="Choose Folder",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            corner_radius=8,
            fg_color=VELORA_ROYAL_BLUE,
            hover_color=VELORA_PURPLE,
            command=self.choose_sync_folder
        )
        self.sync_btn.pack(padx=15, pady=(0, 12), fill="x")
        
        # Storage info
        storage_frame = ctk.CTkFrame(self.sidebar, fg_color=VELORA_CARD_BG, corner_radius=10)
        storage_frame.pack(side="bottom", padx=15, pady=20, fill="x")
        
        ctk.CTkLabel(
            storage_frame,
            text="☁️ Cloud Storage",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=VELORA_LIGHT_GRAY
        ).pack(anchor="w", padx=15, pady=(10, 5))
        
        self.storage_label = ctk.CTkLabel(
            storage_frame,
            text="0 files",
            font=ctk.CTkFont(size=14)
        )
        self.storage_label.pack(anchor="w", padx=15, pady=(2, 10))

        # Main Content Area
        self.main_container = ctk.CTkFrame(self, corner_radius=0, fg_color=VELORA_DARK_BG)
        self.main_container.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(2, weight=1)

        # Top Bar
        top_bar = ctk.CTkFrame(self.main_container, fg_color=VELORA_NAVY, corner_radius=0, height=80)
        top_bar.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        top_bar.grid_propagate(False)
        
        title_label = ctk.CTkLabel(
            top_bar,
            text="☁️ My Cloud Files",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=VELORA_ROYAL_BLUE
        )
        title_label.pack(side="left", padx=30, pady=20)
        
        # Search box
        self.search_entry = ctk.CTkEntry(
            top_bar,
            placeholder_text="✓ Search files...",
            width=300,
            height=40,
            corner_radius=20,
            font=ctk.CTkFont(size=13)
        )
        self.search_entry.pack(side="right", padx=30, pady=20)
        self.search_entry.bind("<KeyRelease>", self.search_files)

        # Action Bar
        action_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=60)
        action_bar.grid(row=1, column=0, sticky="ew", padx=20, pady=(15, 10))
        
        self.refresh_btn = ctk.CTkButton(
            action_bar,
            text="↻ Refresh",
            command=self.load_files,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            width=120,
            corner_radius=8,
            fg_color=VELORA_PURPLE,
            hover_color=VELORA_ACCENT
        )
        self.refresh_btn.pack(side="left", padx=5)

        self.up_btn = ctk.CTkButton(
            action_bar,
            text="⬅ Up",
            command=self.go_up_folder,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            width=90,
            corner_radius=8,
            fg_color=VELORA_CARD_BG,
            hover_color=VELORA_NAVY
        )
        self.up_btn.pack(side="left", padx=5)
        
        self.download_btn = ctk.CTkButton(
            action_bar,
            text="☁️ ↓ Download",
            command=self.download_selected,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            width=140,
            corner_radius=8,
            fg_color=VELORA_ROYAL_BLUE,
            hover_color=VELORA_PURPLE
        )
        self.download_btn.pack(side="left", padx=5)

        self.set_sync_btn = ctk.CTkButton(
            action_bar,
            text="📁 Set Sync Folder",
            command=self.choose_sync_folder,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            width=170,
            corner_radius=8,
            fg_color=VELORA_ROYAL_BLUE,
            hover_color=VELORA_PURPLE
        )
        self.set_sync_btn.pack(side="left", padx=5)
        
        self.delete_btn = ctk.CTkButton(
            action_bar,
            text="✗ Delete",
            command=self.delete_selected,
            font=ctk.CTkFont(size=13, weight="bold"),
            height=35,
            width=120,
            corner_radius=8,
            fg_color=VELORA_GRAY,
            hover_color="#6B6B6B"
        )
        self.delete_btn.pack(side="left", padx=5)
        
        # File count label
        self.file_count_label = ctk.CTkLabel(
            action_bar,
            text="0 files",
            font=ctk.CTkFont(size=13),
            text_color=VELORA_LIGHT_GRAY
        )
        self.file_count_label.pack(side="right", padx=10)

        self.path_label = ctk.CTkLabel(
            action_bar,
            text="Path: /",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY
        )
        self.path_label.pack(side="right", padx=10)

        self.sync_status_label = ctk.CTkLabel(
            action_bar,
            text="Sync folder: Not set",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY
        )
        self.sync_status_label.pack(side="right", padx=10)

        # Files Display Area with custom scrollbar
        self.files_frame = ctk.CTkScrollableFrame(
            self.main_container,
            corner_radius=0,
            fg_color="transparent",
            scrollbar_button_color=VELORA_ROYAL_BLUE,
            scrollbar_button_hover_color=VELORA_PURPLE
        )
        self.files_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 10))
        self.files_frame.grid_columnconfigure(0, weight=1)

        # Status Bar
        status_bar = ctk.CTkFrame(self.main_container, fg_color=VELORA_NAVY, corner_radius=0, height=35)
        status_bar.grid(row=3, column=0, sticky="ew", padx=0, pady=0)
        status_bar.grid_propagate(False)
        
        self.status_label = ctk.CTkLabel(
            status_bar,
            text="✓ Ready",
            font=ctk.CTkFont(size=12),
            text_color=VELORA_LIGHT_GRAY
        )
        self.status_label.pack(side="left", padx=20)

        saved_folders = load_user_sync_folders(self.user[0], self.user[4])
        active_count = 0
        for saved_folder in saved_folders:
            if saved_folder and os.path.isdir(saved_folder):
                self._activate_sync_folder(saved_folder, persist=False)
                active_count += 1

        if active_count:
            self.status_label.configure(text=f"✓ Auto-sync is active ({active_count} folder{'s' if active_count != 1 else ''})")

        self.load_files()

    def _format_sync_path(self, folder_path, max_length=28):
        if len(folder_path) <= max_length:
            return folder_path
        return "..." + folder_path[-(max_length - 3):]

    def choose_sync_folder(self):
        folder_path = filedialog.askdirectory(title="Select a folder to auto-sync")
        if not folder_path:
            return

        try:
            newly_added = self._activate_sync_folder(folder_path)
            if newly_added:
                self.status_label.configure(text="✓ Auto-sync folder is active")
            else:
                self.status_label.configure(text="✓ Folder is already active for auto-sync")
            messagebox.showinfo(
                "Auto-Sync Enabled",
                "New or changed files in this folder will be uploaded to Velora Cloud automatically.\n"
                "Deleting files locally will NOT delete them from Velora Cloud."
            )
        except Exception as error:
            messagebox.showerror("Sync Error", f"Failed to start folder sync:\n{str(error)}")

    def _update_sync_folder_labels(self):
        if not self.sync_services:
            self.sync_folder_label.configure(text="Not set", text_color=VELORA_LIGHT_GRAY)
            self.sync_status_label.configure(text="Sync folder: Not set", text_color=VELORA_LIGHT_GRAY)
            return

        folder_paths = sorted(self.sync_services.keys(), key=lambda folder: folder.lower())
        primary_folder = folder_paths[0]
        extra_count = len(folder_paths) - 1
        label_text = self._format_sync_path(primary_folder)
        status_text = f"Sync folder: {self._format_sync_path(primary_folder, max_length=35)}"

        if extra_count > 0:
            label_text = f"{label_text} (+{extra_count})"
            status_text = f"{status_text} (+{extra_count})"

        self.sync_folder_label.configure(text=label_text, text_color=VELORA_ROYAL_BLUE)
        self.sync_status_label.configure(text=status_text, text_color=VELORA_ROYAL_BLUE)

    def _activate_sync_folder(self, folder_path, persist=True):
        normalized_path = os.path.abspath(folder_path)
        if not os.path.isdir(normalized_path):
            raise FileNotFoundError("Selected folder does not exist")

        if normalized_path in self.sync_services:
            self.sync_folder_path = normalized_path
            self._update_sync_folder_labels()
            return False

        sync_service = FolderSyncService(
            user_id=self.user[0],
            group_id=self.user[4],
            on_sync=self._on_folder_file_synced,
            on_error=self._on_folder_sync_error
        )
        sync_service.set_folder(normalized_path)
        sync_service.start()

        self.sync_services[normalized_path] = sync_service
        self.sync_folder_path = normalized_path
        if persist:
            save_user_sync_folder(self.user[0], self.user[4], normalized_path)

        self._update_sync_folder_labels()
        return True

    def _request_refresh(self):
        if self._refresh_job:
            return
        self._refresh_job = self.after(250, self._flush_refresh)

    def _flush_refresh(self):
        self._refresh_job = None
        self.load_files()

    def _on_folder_file_synced(self, filename, action):
        def update_ui():
            self.status_label.configure(text=f"✓ Auto-sync {action}: {filename}")
            self._request_refresh()

        self.after(0, update_ui)

    def _on_folder_sync_error(self, error_message):
        def update_ui():
            self.status_label.configure(text=f"✗ Auto-sync error: {error_message}")

        self.after(0, update_ui)

    def on_close(self):
        if self._refresh_job:
            self.after_cancel(self._refresh_job)
            self._refresh_job = None

        for sync_service in self.sync_services.values():
            sync_service.stop()

        self.sync_services = {}
        self.destroy()

    def _normalize_storage_path(self, path):
        return os.path.normpath(path).replace("\\", "/").strip("/")

    def _current_folder_prefix(self):
        return f"{self.current_folder}/" if self.current_folder else ""

    def _extract_top_level_folders(self, files, folders):
        top_level_names = set()

        for folder in folders:
            folder_path = self._normalize_storage_path(folder[0])
            if not folder_path:
                continue
            top_level_names.add(folder_path.split("/", 1)[0])

        for file in files:
            file_path = self._normalize_storage_path(file[0])
            if not file_path:
                continue
            if "/" in file_path:
                top_level_names.add(file_path.split("/", 1)[0])

        return top_level_names

    def _auto_discover_matching_sync_folders(self, files, folders):
        if self._auto_discovering_sync or not self.sync_services:
            return

        top_level_names = self._extract_top_level_folders(files, folders)
        if not top_level_names:
            return

        self._auto_discovering_sync = True
        added_count = 0
        try:
            parent_dirs = {
                os.path.dirname(sync_path)
                for sync_path in self.sync_services.keys()
                if os.path.dirname(sync_path)
            }

            for parent_dir in parent_dirs:
                for folder_name in top_level_names:
                    candidate_path = os.path.abspath(os.path.join(parent_dir, folder_name))
                    if candidate_path in self.sync_services:
                        continue
                    if os.path.isdir(candidate_path):
                        try:
                            if self._activate_sync_folder(candidate_path, persist=True):
                                added_count += 1
                        except Exception:
                            continue
        finally:
            self._auto_discovering_sync = False

        if added_count:
            self.status_label.configure(
                text=f"✓ Auto-sync expanded: +{added_count} folder{'s' if added_count != 1 else ''}"
            )

    def _visible_entries(self, files, folders, search_term=""):
        folder_entries = {}
        visible_files = []
        prefix = self._current_folder_prefix()

        for folder in folders:
            full_folder_path = self._normalize_storage_path(folder[0])
            if not full_folder_path:
                continue

            if prefix:
                if not full_folder_path.startswith(prefix):
                    continue
                relative_folder_path = full_folder_path[len(prefix):]
            else:
                relative_folder_path = full_folder_path

            if not relative_folder_path:
                continue

            path_parts = relative_folder_path.split("/", 1)
            folder_name = path_parts[0]
            folder_path = f"{prefix}{folder_name}" if prefix else folder_name

            if not search_term or search_term in relative_folder_path.lower() or search_term in folder_name.lower():
                folder_entries[folder_path] = folder_name

        for file in files:
            full_path = self._normalize_storage_path(file[0])

            if prefix:
                if not full_path.startswith(prefix):
                    continue
                relative_path = full_path[len(prefix):]
            else:
                relative_path = full_path

            if not relative_path:
                continue

            path_parts = relative_path.split("/", 1)

            if len(path_parts) > 1:
                folder_name = path_parts[0]
                folder_path = f"{prefix}{folder_name}" if prefix else folder_name
                if not search_term or search_term in relative_path.lower() or search_term in folder_name.lower():
                    folder_entries[folder_path] = folder_name
            else:
                file_name = path_parts[0]
                if not search_term or search_term in file_name.lower():
                    visible_files.append(file)

        sorted_folders = sorted(folder_entries.items(), key=lambda folder_item: folder_item[1].lower())
        return sorted_folders, visible_files

    def show_root_files(self):
        self.current_folder = ""
        self.selected_file = None
        self.load_files()

    def open_folder(self, folder_path):
        self.current_folder = self._normalize_storage_path(folder_path)
        self.selected_file = None
        self.load_files()

    def go_up_folder(self):
        if not self.current_folder:
            return

        parent_folder = os.path.dirname(self.current_folder)
        self.current_folder = "" if parent_folder in ("", ".") else parent_folder.replace("\\", "/")
        self.selected_file = None
        self.load_files()

    def load_files(self):
        # Clear existing widgets
        for widget in self.files_frame.winfo_children():
            widget.destroy()
        
        # Preserve the current selection
        # self.selected_file = None
        files = get_group_files(self.user[4])
        folders = get_group_folders(self.user[4])
        search_term = self.search_entry.get().strip().lower()

        self._auto_discover_matching_sync_folders(files, folders)

        all_paths = {self._normalize_storage_path(file[0]) for file in files}
        if self.selected_file and self._normalize_storage_path(self.selected_file) not in all_paths:
            self.selected_file = None

        if self.current_folder:
            current_prefix = self._current_folder_prefix()
            folder_paths = {self._normalize_storage_path(folder[0]) for folder in folders}
            if not any(path.startswith(current_prefix) for path in all_paths) and not any(path.startswith(current_prefix) for path in folder_paths):
                self.current_folder = ""

        self.path_label.configure(text=f"Path: /{self.current_folder}" if self.current_folder else "Path: /")
        self.up_btn.configure(state="normal" if self.current_folder else "disabled")

        visible_folders, visible_files = self._visible_entries(files, folders, search_term)
        
        if not files and not folders:
            empty_frame = ctk.CTkFrame(self.files_frame, fg_color="transparent")
            empty_frame.pack(expand=True, fill="both")
            
            ctk.CTkLabel(
                empty_frame,
                text="☁️",
                font=ctk.CTkFont(size=80),
                text_color=VELORA_ROYAL_BLUE
            ).pack(pady=(80, 10))
            
            ctk.CTkLabel(
                empty_frame,
                text="No files yet",
                font=ctk.CTkFont(size=20, weight="bold"),
                text_color=VELORA_ROYAL_BLUE
            ).pack(pady=5)
            
            ctk.CTkLabel(
                empty_frame,
                text="Upload your first file to get started",
                font=ctk.CTkFont(size=14),
                text_color=VELORA_LIGHT_GRAY
            ).pack(pady=5)
            
            self.status_label.configure(text="No files in storage")
            self.file_count_label.configure(text="0 files")
            self.storage_label.configure(text="0 files")
        else:
            if not visible_folders and not visible_files:
                ctk.CTkLabel(
                    self.files_frame,
                    text="No folders or files in this location",
                    font=ctk.CTkFont(size=14),
                    text_color=VELORA_LIGHT_GRAY
                ).pack(pady=50)
                self.status_label.configure(text="No matching items")
                self.file_count_label.configure(text="0 items")
                self.storage_label.configure(text=f"{len(files)} file{'s' if len(files) != 1 else ''}")
                return

            # Table header
            header = ctk.CTkFrame(self.files_frame, fg_color=VELORA_CARD_BG, corner_radius=8, height=45)
            header.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 10))
            header.grid_columnconfigure(1, weight=1)
            header.grid_propagate(False)
            
            ctk.CTkLabel(header, text="Type", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, width=60).grid(row=0, column=0, padx=15)
            ctk.CTkLabel(header, text="File Name", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, anchor="w").grid(row=0, column=1, sticky="w", padx=10)
            ctk.CTkLabel(header, text="Folder", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, width=180, anchor="w").grid(row=0, column=2, sticky="w", padx=10)
            ctk.CTkLabel(header, text="Date", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, width=150).grid(row=0, column=3, padx=10)
            ctk.CTkLabel(header, text="Owner", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, width=100).grid(row=0, column=4, padx=10)
            ctk.CTkLabel(header, text="Actions", font=ctk.CTkFont(size=12, weight="bold"), text_color=VELORA_ROYAL_BLUE, width=100).grid(row=0, column=5, padx=15)

            row_index = 1

            for folder_path, folder_name in visible_folders:
                folder_frame = ctk.CTkFrame(self.files_frame, corner_radius=8, fg_color=VELORA_CARD_BG, height=55)
                folder_frame.grid(row=row_index, column=0, sticky="ew", padx=5, pady=3)
                folder_frame.grid_columnconfigure(1, weight=1)
                folder_frame.grid_propagate(False)

                icon_label = ctk.CTkLabel(folder_frame, text="📁", font=ctk.CTkFont(size=24), width=60)
                icon_label.grid(row=0, column=0, padx=15)

                name_label = ctk.CTkLabel(
                    folder_frame,
                    text=folder_name,
                    font=ctk.CTkFont(size=13, weight="bold"),
                    anchor="w"
                )
                name_label.grid(row=0, column=1, sticky="w", padx=10)

                folder_column_text = self.current_folder if self.current_folder else "Root"
                folder_label = ctk.CTkLabel(
                    folder_frame,
                    text=folder_column_text,
                    font=ctk.CTkFont(size=12),
                    text_color=VELORA_LIGHT_GRAY,
                    anchor="w",
                    width=180
                )
                folder_label.grid(row=0, column=2, sticky="w", padx=10)

                date_label = ctk.CTkLabel(folder_frame, text="-", font=ctk.CTkFont(size=12), text_color=VELORA_LIGHT_GRAY, width=150)
                date_label.grid(row=0, column=3, padx=10)

                owner_label = ctk.CTkLabel(folder_frame, text="-", font=ctk.CTkFont(size=12), text_color=VELORA_LIGHT_GRAY, width=100)
                owner_label.grid(row=0, column=4, padx=10)

                action_btn = ctk.CTkButton(
                    folder_frame,
                    text="→",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    width=35,
                    height=35,
                    corner_radius=6,
                    fg_color=VELORA_ROYAL_BLUE,
                    hover_color=VELORA_PURPLE,
                    command=lambda path=folder_path: self.open_folder(path)
                )
                action_btn.grid(row=0, column=5, padx=15)

                for widget in [folder_frame, icon_label, name_label, folder_label, date_label, owner_label]:
                    widget.bind("<Button-1>", lambda e, path=folder_path: self.open_folder(path))

                row_index += 1
            
            # File rows
            for file in visible_files:
                file_info = get_file_info(file[0], self.user[4])
                file_path = file[0].replace("\\", "/")
                file_name = os.path.basename(file_path)
                folder_name = os.path.dirname(file_path) if "/" in file_path else "Root"
                display_name = file_name
                
                # Highlight selected file
                is_selected = self._normalize_storage_path(file[0]) == self._normalize_storage_path(self.selected_file) if self.selected_file else False
                bg_color = VELORA_PURPLE if is_selected else VELORA_CARD_BG
                
                file_frame = ctk.CTkFrame(self.files_frame, corner_radius=8, fg_color=bg_color, height=55)
                file_frame.grid(row=row_index, column=0, sticky="ew", padx=5, pady=3)
                file_frame.grid_columnconfigure(1, weight=1)
                file_frame.grid_propagate(False)
                
                # File icon
                if file_name.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                    icon = "🖼️"
                elif file_name.endswith(('.pdf', '.doc', '.docx', '.txt')):
                    icon = "📄"
                elif file_name.endswith(('.zip', '.rar', '.7z')):
                    icon = "📦"
                else:
                    icon = "☁️"
                icon_label = ctk.CTkLabel(file_frame, text=icon, font=ctk.CTkFont(size=24), width=60)
                icon_label.grid(row=0, column=0, padx=15)
                
                # File name
                name_label = ctk.CTkLabel(
                    file_frame,
                    text=display_name,
                    font=ctk.CTkFont(size=13),
                    anchor="w"
                )
                name_label.grid(row=0, column=1, sticky="w", padx=10)

                folder_label = ctk.CTkLabel(
                    file_frame,
                    text=self.current_folder if self.current_folder else "Root",
                    font=ctk.CTkFont(size=12),
                    text_color=VELORA_LIGHT_GRAY,
                    anchor="w",
                    width=180
                )
                folder_label.grid(row=0, column=2, sticky="w", padx=10)
                
                # Date
                date_text = file_info['date'] if file_info else "N/A"
                date_label = ctk.CTkLabel(file_frame, text=date_text, font=ctk.CTkFont(size=12), text_color=VELORA_LIGHT_GRAY, width=150)
                date_label.grid(row=0, column=3, padx=10)
                
                # Owner
                owner_text = file_info['owner'] if file_info else "Unknown"
                owner_label = ctk.CTkLabel(file_frame, text=owner_text, font=ctk.CTkFont(size=12), text_color=VELORA_LIGHT_GRAY, width=100)
                owner_label.grid(row=0, column=4, padx=10)
                
                # Action button
                action_btn = ctk.CTkButton(
                    file_frame,
                    text="✓",
                    font=ctk.CTkFont(size=18, weight="bold"),
                    width=35,
                    height=35,
                    corner_radius=6,
                    fg_color=VELORA_ROYAL_BLUE,
                    hover_color=VELORA_PURPLE,
                    command=lambda f=file[0]: self.select_file(f)
                )
                action_btn.grid(row=0, column=5, padx=15)
                
                # Make entire row clickable
                for widget in [file_frame, icon_label, name_label, folder_label, date_label, owner_label]:
                    widget.bind("<Button-1>", lambda e, f=file[0]: self.select_file(f))
                row_index += 1
            
            item_count = len(visible_folders) + len(visible_files)
            if search_term:
                self.status_label.configure(text=f"✓ Found {item_count} item(s)")
            else:
                self.status_label.configure(text=f"✓ Loaded {item_count} item(s)")
            self.file_count_label.configure(text=f"{item_count} item{'s' if item_count != 1 else ''}")
            self.storage_label.configure(text=f"{len(files)} file{'s' if len(files) != 1 else ''}")

    def select_file(self, filename):
        self.selected_file = self._normalize_storage_path(filename)
        self.status_label.configure(text=f"Selected: {filename}")
        self.load_files()  # Refresh to show selection
        
    def search_files(self, event):
        self.load_files()

    def upload_file(self):
        file_path = filedialog.askopenfilename(title="Select a file to upload")
        if file_path:
            filename = os.path.basename(file_path)
            try:
                with open(file_path, "rb") as source_file:
                    content = source_file.read()

                cloud_filename = f"{self.current_folder}/{filename}" if self.current_folder else filename
                save_file(cloud_filename, self.user[0], self.user[4], content)
                self.status_label.configure(text=f"✓ Successfully uploaded: {cloud_filename}")
                self.load_files()
                messagebox.showinfo("Success", f"File '{filename}' uploaded successfully!")
            except Exception as e:
                self.status_label.configure(text=f"✗ Upload failed: {str(e)}")
                messagebox.showerror("Error", f"Failed to upload file:\n{str(e)}")

    def upload_folder(self):
        folder_path = filedialog.askdirectory(title="Select a folder to upload")
        if not folder_path:
            return

        folder_path = os.path.abspath(folder_path)
        folder_name = os.path.basename(folder_path.rstrip("\\/")) or "UploadedFolder"

        try:
            save_folder(folder_name, self.user[0], self.user[4])

            uploaded_count = 0
            for root, dirs, files in os.walk(folder_path):
                relative_root = os.path.relpath(root, folder_path).replace("\\", "/")
                if relative_root == ".":
                    cloud_root = folder_name
                else:
                    cloud_root = f"{folder_name}/{relative_root}"

                save_folder(cloud_root, self.user[0], self.user[4])

                for directory_name in dirs:
                    save_folder(f"{cloud_root}/{directory_name}", self.user[0], self.user[4])

                for local_filename in files:
                    local_file_path = os.path.join(root, local_filename)
                    cloud_filename = f"{cloud_root}/{local_filename}" if cloud_root else local_filename
                    with open(local_file_path, "rb") as source_file:
                        content = source_file.read()
                    save_file(cloud_filename, self.user[0], self.user[4], content)
                    uploaded_count += 1

            self._activate_sync_folder(folder_path)

            self.current_folder = ""
            self.selected_file = None
            self.load_files()

            if uploaded_count == 0:
                self.status_label.configure(text=f"✓ Folder uploaded + auto-sync active: {folder_name} (empty)")
                messagebox.showinfo(
                    "Success",
                    f"Folder '{folder_name}' uploaded successfully!\n"
                    "(No files inside yet)\n\n"
                    "Auto-sync is now active for this folder."
                )
            else:
                self.status_label.configure(text=f"✓ Folder uploaded + auto-sync active: {folder_name} ({uploaded_count} files)")
                messagebox.showinfo(
                    "Success",
                    f"Folder '{folder_name}' uploaded with {uploaded_count} file(s).\n\n"
                    "Auto-sync is now active for this folder."
                )
        except Exception as e:
            self.status_label.configure(text=f"✗ Folder upload failed: {str(e)}")
            messagebox.showerror("Error", f"Failed to upload folder:\n{str(e)}")

    def download_selected(self):
        if not self.selected_file:
            messagebox.showwarning("No Selection", "Please select a file first!")
            return
        
        save_path = filedialog.asksaveasfilename(
            initialfile=os.path.basename(self.selected_file),
            title="Save file as"
        )
        
        if save_path:
            try:
                source = download_file(self.selected_file, self.user[4])
                with open(source, "rb") as src:
                    content = src.read()
                    with open(save_path, "wb") as dst:
                        dst.write(content)
                
                self.status_label.configure(text=f"✓ Downloaded: {self.selected_file}")
                messagebox.showinfo("Success", f"File downloaded successfully to:\n{save_path}")
            except FileNotFoundError as e:
                messagebox.showerror("File Not Found", f"The file could not be found:\n{str(e)}")
                self.status_label.configure(text=f"✗ Download failed: File not found")
            except PermissionError as e:
                messagebox.showerror("Permission Denied", f"You don't have access to this file:\n{str(e)}")
                self.status_label.configure(text=f"✗ Download failed: Permission denied")
            except Exception as e:
                messagebox.showerror("Download Error", f"Failed to download:\n{str(e)}")
                self.status_label.configure(text=f"✗ Download failed")

    def delete_selected(self):
        if not self.selected_file:
            messagebox.showwarning("No Selection", "Please select a file first!")
            return
        
        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{self.selected_file}'?\nThis action cannot be undone."
        )
        
        if confirm:
            try:
                delete_file_from_storage(self.selected_file, self.user[4])
                self.status_label.configure(text=f"✗ Deleted: {self.selected_file}")
                self.selected_file = None
                self.load_files()
                messagebox.showinfo("Success", "File deleted successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete file:\n{str(e)}")
