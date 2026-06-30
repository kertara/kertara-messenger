import tkinter as tk
import os
import sys
import gc

def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class BaseDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        try:
            icon_path = get_resource_path(os.path.join("assets", "icon.ico"))
            self.iconbitmap(icon_path)
        except Exception:
            pass

class RenameDialog(BaseDialog):
    def __init__(self, parent, current_name):
        super().__init__(parent)
        self.title("Rename Contact")
        self.geometry("300x120")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None
        self.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 50}")

        tk.Label(self, text="Enter new alias name:", font=("Arial", 9, "bold")).pack(pady=(10, 5))
        
        self.entry = tk.Entry(self, font=("Arial", 10), width=30)
        self.entry.insert(0, current_name)
        self.entry.selection_range(0, tk.END)
        self.entry.pack(pady=5, padx=15)
        self.entry.focus_set()

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Save", width=10, command=self.on_save, bg="#d4edda").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Cancel", width=10, command=self.on_cancel).pack(side="right", padx=5)

        self.bind("<Return>", lambda e: self.on_save())
        self.bind("<Escape>", lambda e: self.on_cancel())
        
        self.wait_window(self)

    def on_save(self):
        self.result = self.entry.get().strip()
        self.destroy()
        gc.collect()

    def on_cancel(self):
        self.result = None
        self.destroy()
        gc.collect()