import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk
import requests
import webbrowser
import gc
from config import AppConfig
from database import ChatDatabase
from network import NetworkManager
from gui.chat_page import ChatPage

class KertaraGUI:
    current_version = "0.1.0-alpha"

    def __init__(self, root, user_profile=None):
        self.root = root
        self.root.withdraw()
        self.root.title(f"Kertara Messenger v{self.current_version}")
        self.root.geometry("900x600")
        position_right = int(self.root.winfo_screenwidth() / 2 - 900 / 2)
        position_top = int(self.root.winfo_screenheight() / 2 - 600 / 2)
        self.root.geometry(f"+{position_right}+{position_top}")
        
        if not self.check_version_blocking():
            self.root.destroy()
            return
            
        self.root.deiconify()
        self.config = AppConfig(user_profile=user_profile)
        self.icon_path = self.get_resource_path(os.path.join("assets", "icon.ico"))
        self.main_container = tk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)
        if os.path.exists(self.icon_path):
            try: self.root.iconbitmap(self.icon_path)
            except: pass
        self.show_login_screen()

    def show_login_screen(self):
        self.login_frame = tk.Frame(self.main_container)
        self.login_frame.place(relx=0.5, rely=0.5, anchor="center")
        prompt = "Create a new Master Password:" if not os.path.exists(self.config.vault_meta_file) else "Enter your Master Password:"
        tk.Label(self.login_frame, text=prompt, font=("Arial", 12)).pack(pady=10)
        self.entry = tk.Entry(self.login_frame, show="*", width=30, font=("Arial", 12))
        self.entry.pack(pady=10)
        self.entry.bind("<Key>", lambda e: self.error_label.config(text=""))
        tk.Button(self.login_frame, text="Unlock", command=self.attempt_unlock, width=15).pack(pady=10)
        self.entry.bind("<Return>", lambda e: self.attempt_unlock())
        self.error_label = tk.Label(self.login_frame, text="", fg="red", font=("Arial", 10))
        self.error_label.pack(pady=5)

    def attempt_unlock(self):
        pwd = self.entry.get()
        self.entry.delete(0, tk.END)
        if not os.path.exists(self.config.vault_meta_file):
            self.config.initialize_vault(pwd)
        elif not self.config.unlock_vault(pwd):
            self.error_label.config(text="Invalid password! Please try again.")
            pwd = ""
            return
        pwd = ""
        self.login_frame.destroy()
        gc.collect()
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except: pass
        self.style = ttk.Style()
        if 'vista' in self.style.theme_names(): self.style.theme_use('vista')
        elif 'xpnative' in self.style.theme_names(): self.style.theme_use('xpnative')
        self.active_contact = None
        self.contact_mapping = []
        self.db = ChatDatabase(self.config)
        self.network = NetworkManager(self.config, self.db)
        self.chat_page = ChatPage(self)

    def get_resource_path(self, relative_path):
        try: base_path = sys._MEIPASS
        except Exception: base_path = os.path.abspath(".")
        return os.path.join(base_path, relative_path)

    def check_version_blocking(self):
        url = "https://raw.githubusercontent.com/kertara/kertara.github.io/refs/heads/main/projects/kertara-messenger/version.json"
        try:
            response = requests.get(url, timeout=5, headers={"Cache-Control": "no-cache"})
            data = response.json()
            
            if data.get("maintenance", {}).get("mode", False):
                messagebox.showerror("Maintenance", data["maintenance"]["message"])
                return False

            def version_to_tuple(v_str):
                clean_v = v_str.split('-')[0]
                return tuple(map(int, clean_v.split('.')))

            min_ver = data["compatibility"]["min_required_version"]
            if version_to_tuple(min_ver) > version_to_tuple(self.current_version):
                loc = data["ui_localization"]
                if messagebox.askyesno(loc["title"], loc["message"]):
                    webbrowser.open(data["update_policy"]["update_url"])
                return False
            return True
        except Exception: return True

    def clear_container(self):
        for widget in self.main_container.winfo_children():
            widget.destroy()
        self.root.config(menu="")
        gc.collect()

    def build_notepad_style_navbar(self, chat_ref):
        menubar = tk.Menu(self.root)
        identity_menu = tk.Menu(menubar, tearoff=0)
        identity_menu.add_command(label="Copy My KRT Address", command=chat_ref.copy_my_address)
        identity_menu.add_separator()
        identity_menu.add_command(label="Reset KRT Identity", command=self.action_reset_onion)
        menubar.add_cascade(label="Identity", menu=identity_menu)
        help_menu = tk.Menu(menubar, tearoff=0)
        def show_detailed_about():
            about_text = "Kertara Messenger v0.1.0-alpha"
            messagebox.showinfo("About Kertara", about_text)
        help_menu.add_command(label="About Kertara", command=show_detailed_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menubar)

    def action_reset_onion(self):
        if messagebox.askyesno("Wipe Identity Control", "Are you absolutely sure?"):
            self.network.reset_onion_address()
            self.root.destroy()

    def reset_chat_header(self):
        if hasattr(self, 'warning_banner') and self.warning_banner.winfo_ismapped():
            self.warning_banner.pack_forget()
        if hasattr(self, 'lbl_chat_with'):
            self.lbl_chat_with.config(
                text="Please select a contact from the sidebar to begin encrypted chat", 
                font=("Arial", 10, "italic"), 
                fg="gray"
            )
        if hasattr(self, 'chat_display_area'):
            self.chat_display_area.config(state="normal")
            self.chat_display_area.delete('1.0', tk.END)
            self.chat_display_area.config(state="disabled")