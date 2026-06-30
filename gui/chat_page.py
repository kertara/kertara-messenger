import os
import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import time
import json
import gc

class ChatPage:
    def __init__(self, gui_base):
        self.base = gui_base
        self.current_chat_onion = self.base.active_contact
        self.base.build_notepad_style_navbar(self)
        paned = tk.PanedWindow(self.base.main_container, orient="horizontal", bd=2, relief="groove")
        paned.pack(fill="both", expand=True)
        sidebar = tk.Frame(paned, width=300, bd=1, relief="sunken")
        sidebar.pack_propagate(False)
        paned.add(sidebar)
        chat_area = tk.Frame(paned)
        paned.add(chat_area)
        info_frame = tk.LabelFrame(sidebar, text="Connection & Quick Controls")
        info_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_tor_status = tk.Label(info_frame, text="TOR: CONNECTING (0%)", fg="orange", font=("Arial", 9, "bold"))
        self.lbl_tor_status.pack(anchor="w", padx=5, pady=2)
        self.progress_bar = ttk.Progressbar(info_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill="x", padx=5, pady=2)
        copy_frame = tk.Frame(info_frame)
        copy_frame.pack(fill="x", padx=5, pady=5)
        self.ent_my_onion = tk.Entry(copy_frame, state="readonly", font=("Courier", 9))
        self.ent_my_onion.pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.btn_quick_copy = tk.Button(copy_frame, text="Copy", command=self.copy_my_address, bg="#e1e1e1", width=10)
        self.btn_quick_copy.pack(side="right")
        add_frame = tk.LabelFrame(sidebar, text="Add New Contact")
        add_frame.pack(fill="x", padx=5, pady=5)
        tk.Label(add_frame, text="Contact KRT Address:").pack(anchor="w", padx=5)
        self.ent_new_onion = tk.Entry(add_frame)
        self.ent_new_onion.pack(fill="x", padx=5, pady=2)
        tk.Label(add_frame, text="Alias Name:").pack(anchor="w", padx=5)
        self.ent_new_alias = tk.Entry(add_frame)
        self.ent_new_alias.pack(fill="x", padx=5, pady=2)
        tk.Button(add_frame, text="Save Contact", command=self.add_contact, bg="#d4edda").pack(fill="x", padx=5, pady=5)
        vault_frame = tk.LabelFrame(sidebar, text="Contacts Vault")
        vault_frame.pack(fill="both", expand=True, padx=5, pady=5)
        vault_inner = tk.Frame(vault_frame)
        vault_inner.pack(fill="both", expand=True, padx=2, pady=2)
        self.contact_scrollbar = tk.Scrollbar(vault_inner, orient="vertical")
        self.contact_scrollbar.pack(side="right", fill="y")
        self.contact_listbox = tk.Listbox(vault_inner, font=("Arial", 10), yscrollcommand=self.contact_scrollbar.set)
        self.contact_listbox.pack(side="left", fill="both", expand=True)
        self.contact_scrollbar.config(command=self.contact_listbox.yview)
        self.contact_listbox.bind("<<ListboxSelect>>", self.on_contact_selected)
        self.contact_listbox.bind("<Button-3>", self.show_context_menu)
        self.contact_listbox.bind("<Button-2>", self.show_context_menu)
        self.popup_menu = tk.Menu(self.base.root, tearoff=0)
        self.popup_menu.add_command(label="Rename Contact", command=self.rename_contact_context)
        self.popup_menu.add_command(label="Delete Contact", command=self.delete_contact)
        self.header_frame = tk.Frame(chat_area)
        self.warning_banner = tk.Label(chat_area, text="⚠️ Connection not verified. Please verify your contact to ensure security.", bg="#ffc107", fg="black", font=("Arial", 9, "bold"), pady=5)
        self.header_frame.pack(fill="x", padx=5, pady=5)
        self.lbl_chat_with = tk.Label(self.header_frame, text="Please select a contact from the sidebar to begin encrypted chat", font=("Arial", 10, "italic"), fg="gray")
        self.lbl_chat_with.grid(row=0, column=0, sticky="w")
        self.btn_verify = tk.Button(self.header_frame, command=self.verify_contact_manually)
        self.btn_verify.grid(row=0, column=1, padx=10)
        chat_wrapper = tk.Frame(chat_area)
        chat_wrapper.pack(fill="both", expand=True, padx=5, pady=5)
        self.scrollbar = tk.Scrollbar(chat_wrapper, orient="vertical")
        self.scrollbar.pack(side="right", fill="y")
        self.chat_display = tk.Text(chat_wrapper, state="disabled", bg="#F4F6F7", wrap="word", font=("Arial", 10), yscrollcommand=self.scrollbar.set)
        self.chat_display.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.chat_display.yview)
        self.chat_display.tag_config("kanan", justify="right", background="#DCF8C6", lmargin1=150)
        self.chat_display.tag_config("kiri", justify="left", background="#EAEAEA", rmargin=150)
        self.chat_display.tag_config("error", justify="center", foreground="red", font=("Arial", 9, "bold"))
        input_frame = tk.Frame(chat_area, pady=5)
        input_frame.pack(fill="x", padx=5)
        self.ent_msg = tk.Entry(input_frame, state="disabled", font=("Arial", 11))
        self.ent_msg.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.ent_msg.bind("<Return>", lambda e: self.send_message())
        self.btn_send = tk.Button(input_frame, text="Send", state="disabled", command=self.send_message, width=12, bg="#007bff", fg="white", font=("Arial", 10, "bold"))
        self.btn_send.pack(side="right")
        self.refresh_contact_list()
        threading.Thread(target=self.base.network.jalankan_tor, args=(self.on_tor_progress, self.on_tor_ready, lambda e: None), daemon=True).start()
        threading.Thread(target=self.base.network.listen_incoming, args=(self.handle_incoming_message, self.refresh_chat_display), daemon=True).start()
        self.base.network.start_presence_checker(lambda: self.base.root.after(0, self.refresh_and_update))
        self.btn_verify.grid_remove()

    def update_security_banner(self):
        if not self.base.active_contact:
            self.warning_banner.pack_forget()
            return
        vault = self.base.db.load_vault()
        if self.base.active_contact not in vault:
            self.warning_banner.pack_forget()
            return
        contact_data = vault.get(self.base.active_contact, {})
        is_verified = contact_data.get("is_verified", False)
        if not is_verified:
            self.warning_banner.config(text="⚠️ Connection not verified. Please verify your contact to ensure security.")
            self.warning_banner.pack(fill="x", before=self.chat_display.master)
        else:
            self.warning_banner.pack_forget()

    def show_context_menu(self, event):
        try:
            clicked_index = self.contact_listbox.nearest(event.y)
            if clicked_index < 0 or clicked_index >= self.contact_listbox.size(): return
            self.contact_listbox.selection_clear(0, tk.END)
            self.contact_listbox.selection_set(clicked_index)
            self.contact_listbox.activate(clicked_index)
            self.contact_listbox.focus_set()
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def rename_contact_context(self):
        from gui.dialogs import RenameDialog
        sel = self.contact_listbox.curselection()
        if not sel: return
        index = sel[0]
        target_onion = self.base.contact_mapping[index]
        vault = self.base.db.load_vault()
        current_name = vault[target_onion]["nama"]
        dialog = RenameDialog(self.base.root, current_name)
        if dialog.result and dialog.result != current_name:
            conn = self.base.db._get_conn()
            conn.execute("UPDATE contacts SET nama=? WHERE onion=?", (dialog.result, target_onion))
            conn.commit()
            conn.close()
            self.refresh_contact_list()
            if self.base.active_contact == target_onion:
                self.lbl_chat_with.config(text=f"Secured Channel Active: {dialog.result}")

    def delete_contact(self):
        sel = self.contact_listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a contact from the list to delete.")
            return
        
        index = sel[0]
        target_onion = self.base.contact_mapping[index]
        
        if messagebox.askyesno("Delete Contact", "Are you sure you want to delete this contact?"):
            self.base.db.hapus_kontak_dari_db(target_onion)
            
            if self.base.active_contact == target_onion:
                self.base.active_contact = None
                self.current_chat_onion = None
                
            self.refresh_contact_list()
            
            if hasattr(self, 'warning_banner'):
                self.warning_banner.pack_forget()
            
            self.lbl_chat_with.config(
                text="Please select a contact from the sidebar to begin encrypted chat", 
                font=("Arial", 10, "italic"), 
                fg="gray"
            )
            
            self.chat_display.config(state="normal")
            self.chat_display.delete("1.0", tk.END)
            self.chat_display.config(state="disabled")
            
            self.ent_msg.delete(0, tk.END)
            self.ent_msg.config(state="disabled")
            
            self.btn_send.config(state="disabled")

    def copy_my_address(self):
        self.base.root.clipboard_clear()
        krt_address = self.base.config.onion_to_krt(self.base.network.my_onion_address)
        self.base.root.clipboard_append(krt_address)
        self.btn_quick_copy.config(text="Copied", bg="#d4edda", fg="green")
        self.base.root.after(2000, lambda: self.btn_quick_copy.config(text="Copy", bg="#e1e1e1", fg="black"))

    def add_contact(self):
        import random
        import string
        addr_input = self.ent_new_onion.get().strip()
        alias = self.ent_new_alias.get().strip()
        if not addr_input:
            messagebox.showerror("Error", "KRT Address cannot be empty.")
            return
        if addr_input.startswith("KRT-"):
            addr = self.base.config.krt_to_onion(addr_input)
        else:
            addr = addr_input if addr_input.endswith(".onion") else addr_input + ".onion"
        if not addr or addr == self.base.network.my_onion_address:
            messagebox.showerror("Error", "Invalid address.")
            return
        conn = self.base.db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM contacts WHERE onion=?", (addr,))
        if cursor.fetchone():
            messagebox.showwarning("Info", "Contact already exists.")
            conn.close()
            return
        if not alias: alias = f"User_{''.join(random.choices(string.ascii_letters + string.digits, k=4))}"
        cursor.execute("INSERT INTO contacts VALUES (?, ?, ?, ?, ?)", (addr, alias, 0, None, 0))
        conn.commit()
        conn.close()
        self.ent_new_onion.delete(0, tk.END)
        self.ent_new_alias.delete(0, tk.END)
        self.refresh_contact_list()
        messagebox.showinfo("Success", "Contact added.")

    def on_contact_selected(self, event):
        sel = self.contact_listbox.curselection()
        if sel:
            self.base.active_contact = self.base.contact_mapping[sel[0]]
            self.current_chat_onion = self.base.active_contact
            conn = self.base.db._get_conn()
            conn.execute("UPDATE contacts SET unread=0 WHERE onion=?", (self.base.active_contact,))
            conn.commit()
            conn.close()
            self.refresh_contact_list()
            is_online = self.base.network.online_statuses.get(self.base.active_contact, False)
            status_text = "● Online" if is_online else "○ Offline"
            status_color = "#28a745" if is_online else "gray"
            vault = self.base.db.load_vault()
            self.lbl_chat_with.config(text=f"{vault[self.base.active_contact]['nama']} ({status_text})", font=("Arial", 10, "bold"), fg=status_color)
            self.ent_msg.config(state="normal")
            if self.base.network.is_tor_ready: self.btn_send.config(state="normal")
            self.load_chat_screen()
            self.update_security_banner()

    def update_chat_header(self):
        if not self.base.active_contact:
            self.btn_verify.grid_remove()
            self.lbl_chat_with.config(text="Please select a contact from the sidebar to begin encrypted chat", font=("Arial", 10, "italic"), fg="gray")
            return
        vault = self.base.db.load_vault()
        if self.base.active_contact in vault:
            contact_data = vault[self.base.active_contact]
            is_online = self.base.network.online_statuses.get(self.base.active_contact, False)
            is_verified = contact_data.get("is_verified", False)
            status_text = "● Online" if is_online else "○ Offline"
            status_color = "#28a745" if is_online else "gray"
            self.lbl_chat_with.config(text=f"{contact_data['nama']} ({status_text})", font=("Arial", 10, "bold"), fg=status_color)
            self.btn_verify.grid()
            if is_verified: self.btn_verify.config(text="✓ Verified", state="disabled", bg="#d4edda", fg="green")
            else: self.btn_verify.config(text="⚠️ Verify Now", state="normal", bg="#ffc107", fg="black")
        else: self.btn_verify.grid_remove()

    def refresh_contact_list(self):
        current_sel = self.contact_listbox.curselection()
        self.contact_listbox.delete(0, tk.END)
        vault = self.base.db.load_vault()
        self.base.contact_mapping = list(vault.keys())
        for idx, addr in enumerate(self.base.contact_mapping):
            info = vault[addr]
            krt_preview = f"{self.base.config.onion_to_krt(addr)[:12]}..."
            unread_suffix = f" [{info.get('unread', 0)}]" if info.get('unread', 0) > 0 else ""
            dot = "●" if self.base.network.online_statuses.get(addr, False) else "○"
            self.contact_listbox.insert(tk.END, f"{dot} {info['nama']} ({krt_preview}){unread_suffix}")
            if info.get('unread', 0) > 0: self.contact_listbox.itemconfig(idx, fg="#ff3333")
            elif self.base.network.online_statuses.get(addr, False): self.contact_listbox.itemconfig(idx, fg="#28a745")
        if current_sel and current_sel[0] < len(self.base.contact_mapping): self.contact_listbox.selection_set(current_sel[0])

    def refresh_and_update(self):
        self.refresh_contact_list()
        self.update_chat_header()

    def refresh_chat_display(self):
        self.base.root.after(0, self.load_chat_screen)

    def verify_contact_manually(self):
        vault = self.base.db.load_vault()
        if self.base.active_contact not in vault: return
        peer_pub_hex = vault[self.base.active_contact].get("shared_dh_public")
        if not peer_pub_hex:
            messagebox.showwarning("Verification Error", "Key exchange not complete.")
            return
        my_fp = self.base.config.get_my_fingerprint()
        peer_fp = self.base.config.get_dh_fingerprint(bytes.fromhex(peer_pub_hex))
        if messagebox.askyesno("Verify Fingerprint", f"Confirm fingerprints match:\n\nMine: {my_fp}\nPeer: {peer_fp}"):
            conn = self.base.db._get_conn()
            conn.execute("UPDATE contacts SET is_verified=1 WHERE onion=?", (self.base.active_contact,))
            conn.commit()
            conn.close()
            self.update_chat_header()
            self.update_security_banner()

    def load_chat_screen(self):
        self.chat_display.config(state="normal")
        self.chat_display.delete("1.0", tk.END)
        if self.base.active_contact:
            vault_data = self.base.db.load_vault()
            history = vault_data.get(self.base.active_contact, {}).get("history", [])
            for c in history:
                tag = "kanan" if c["pengirim"] == "Kamu" else "kiri"
                if c["pengirim"] == "Kamu": self.chat_display.insert(tk.END, f" {c['pesan']}   [{c['waktu']}] {c['status']}\n", tag)
                else: self.chat_display.insert(tk.END, f" [{c['waktu']}] {c['pesan']}\n", tag)
        self.chat_display.see(tk.END)
        self.chat_display.config(state="disabled")

    def handle_incoming_message(self, sender, content):
        def gui_update():
            vault = self.base.db.load_vault()
            if sender not in vault:
                conn = self.base.db._get_conn()
                conn.execute("INSERT INTO contacts VALUES (?, ?, ?, ?, ?)", (sender, f"User_{sender[:4]}", 0, None, 0))
                conn.commit()
                conn.close()
            if self.current_chat_onion != sender:
                conn = self.base.db._get_conn()
                conn.execute("UPDATE contacts SET unread=unread+1 WHERE onion=?", (sender,))
                conn.commit()
                conn.close()
                self.refresh_contact_list()
            else: self.load_chat_screen()
        self.base.root.after(0, gui_update)

    def send_message(self):
        msg = self.ent_msg.get().strip()
        if msg and self.base.active_contact:
            msg_id = str(int(time.time() * 1000))
            self.ent_msg.delete(0, tk.END)
            self.base.network.kirim_pesan(self.base.active_contact, msg, msg_id, self.refresh_chat_display)

    def on_tor_progress(self, progress):
        self.lbl_tor_status.config(text=f"TOR CONNECTING: {progress}%")
        self.progress_bar["value"] = progress

    def on_tor_ready(self, address):
        self.lbl_tor_status.config(text="ONLINE (E2EE ACTIVE)", fg="green")
        self.progress_bar.pack_forget()
        self.ent_my_onion.config(state="normal")
        self.ent_my_onion.delete(0, tk.END)
        self.ent_my_onion.insert(0, self.base.config.onion_to_krt(address))
        self.ent_my_onion.config(state="readonly")
        if self.base.active_contact: self.btn_send.config(state="normal")