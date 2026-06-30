import sqlite3
import time
import random
import string
import threading
from cryptography.fernet import Fernet

class ChatDatabase:
    def __init__(self, config_obj):
        self.config = config_obj
        self.db_path = self.config.db_path
        self._init_db()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        return conn

    def _init_db(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS contacts 
                          (onion TEXT PRIMARY KEY, nama TEXT, unread INTEGER, shared_dh_public TEXT, is_verified INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS ratchet_state 
                          (onion TEXT PRIMARY KEY, chain_key BLOB, remote_pub BLOB, counter INTEGER)''')
        cursor.execute('''CREATE TABLE IF NOT EXISTS messages 
                          (id TEXT PRIMARY KEY, onion TEXT, pengirim TEXT, pesan TEXT, waktu TEXT, status TEXT)''')
        conn.commit()
        conn.close()

    def load_vault(self):
        vault = {}
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM contacts")
        for row in cursor.fetchall():
            onion, nama, unread, dh_pub, is_ver = row
            vault[onion] = {
                "nama": nama,
                "unread": unread,
                "shared_dh_public": dh_pub,
                "is_verified": bool(is_ver),
                "history": [],
                "ratchet_state": {"chain_key": None, "remote_pub": None, "counter": 0}
            }
            
            cursor.execute("SELECT * FROM ratchet_state WHERE onion=?", (onion,))
            r_state = cursor.fetchone()
            if r_state:
                vault[onion]["ratchet_state"] = {"chain_key": r_state[1], "remote_pub": r_state[2], "counter": r_state[3]}
                
            cursor.execute("SELECT pengirim, pesan, waktu, status, id FROM messages WHERE onion=? ORDER BY waktu ASC", (onion,))
            for m in cursor.fetchall():
                vault[onion]["history"].append({"pengirim": m[0], "pesan": m[1], "waktu": m[2], "status": m[3], "id": m[4]})
        
        conn.close()
        return vault

    def save_vault(self, data):
        pass

    def simpan_chat(self, onion_address, pengirim, pesan, status="...", msg_id=None):
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute("SELECT 1 FROM contacts WHERE onion=?", (onion_address,))
        if not cursor.fetchone():
            id_rnd = ''.join(random.choices(string.ascii_letters + string.digits, k=4))
            cursor.execute("INSERT INTO contacts VALUES (?, ?, ?, ?, ?)", (onion_address, f"Unknown_{id_rnd}", 0, None, 0))
        
        cursor.execute("INSERT OR REPLACE INTO messages VALUES (?, ?, ?, ?, ?, ?)", 
                       (msg_id, onion_address, pengirim, pesan, time.strftime("%H:%M:%S"), status))
        conn.commit()
        conn.close()

    def update_status_pesan(self, onion_address, msg_id, status_baru):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("UPDATE messages SET status=? WHERE id=? AND onion=?", (status_baru, msg_id, onion_address))
        conn.commit()
        conn.close()

    def update_status_chat(self, onion_kontak, msg_id, new_status):
        self.update_status_pesan(onion_kontak, msg_id, new_status)

    def hapus_kontak_dari_db(self, onion_kontak):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM contacts WHERE onion=?", (onion_kontak,))
        cursor.execute("DELETE FROM messages WHERE onion=?", (onion_kontak,))
        conn.commit()
        conn.close()

    def hapus_pesan_sistem_berstatus(self, status):
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE status=?", (status,))
        conn.commit()
        conn.close()

    def export_data_to_file(self, data_dict):
        cipher = Fernet(self.config.master_exchange_key)
        import json
        return cipher.encrypt(json.dumps(data_dict).encode())

    def import_data_from_file(self, encrypted_bytes):
        cipher = Fernet(self.config.master_exchange_key)
        import json
        return json.loads(cipher.decrypt(encrypted_bytes).decode())