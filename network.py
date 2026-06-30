import socket
import socks
import threading
import time
import re
import os
import json
import base64
import gc
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import x25519
from stem.control import Controller
from stem.process import launch_tor_with_config

def secure_zero(data):
    if isinstance(data, (bytearray, list)):
        for i in range(len(data)):
            data[i] = 0

class NetworkManager:
    def __init__(self, config_obj, db_obj):
        self.config = config_obj
        self.db = db_obj
        self.my_onion_address = "Memuat..."
        self.is_tor_ready = False
        self.online_statuses = {}
        self.session_keys = {}
        self.warning_sent = {}

    def reset_onion_address(self):
        if os.path.exists(self.config.onion_key_file):
            os.remove(self.config.onion_key_file)
        self.my_onion_address = None

    def get_contact_cipher(self, onion_address):
        if onion_address in self.session_keys:
            return self.session_keys[onion_address]
        conn = self.db._get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT shared_dh_public FROM contacts WHERE onion=?", (onion_address,))
        row = cursor.fetchone()
        conn.close()
        if not row or not row[0]: return None
        try:
            peer_public_bytes = bytes.fromhex(row[0])
            peer_public_key = x25519.X25519PublicKey.from_raw_public_bytes(peer_public_bytes)
            my_private_key = self.config.get_dh_private_key()
            shared_key = my_private_key.exchange(peer_public_key)
            derived_key = self.config.get_derived_ratchet_key(shared_key, b"init_handshake")
            cipher = AESGCM(derived_key)
            self.session_keys[onion_address] = (cipher, derived_key)
            return (cipher, derived_key)
        except: return None

    def jalankan_tor(self, on_progress, on_ready, on_error):
        tor_config = {
            'ControlPort': str(self.config.tor_control_port),
            'SocksPort': str(self.config.socks_port),
            'DataDirectory': self.config.tor_data_dir,
        }
        def log_handler(line):
            if "Bootstrapped" in line:
                match = re.search(r"Bootstrapped (\d+)%", line)
                if match: on_progress(int(match.group(1)))
        try:
            for file_name in ['cached-descriptors', 'cached-descriptors.new', 'cached-extrainfo', 'cached-extrainfo.new', 'lock']:
                target_file = os.path.join(self.config.tor_data_dir, file_name)
                if os.path.exists(target_file):
                    try: os.remove(target_file)
                    except: pass
        except Exception: pass
        try:
            launch_tor_with_config(tor_cmd=self.config.tor_path, config=tor_config, take_ownership=True, init_msg_handler=log_handler)
            with Controller.from_port(port=self.config.tor_control_port) as controller:
                controller.authenticate()
                private_key_type, private_key_content = None, None
                if os.path.exists(self.config.onion_key_file):
                    with open(self.config.onion_key_file, 'r') as kf:
                        data_key = kf.read().split(":", 1)
                        if len(data_key) == 2: private_key_type, private_key_content = data_key[0], data_key[1]
                if private_key_type and private_key_content:
                    response = controller.create_ephemeral_hidden_service({80: self.config.local_port}, key_type=private_key_type, key_content=private_key_content, await_publication=True)
                else:
                    response = controller.create_ephemeral_hidden_service({80: self.config.local_port}, await_publication=True)
                    with open(self.config.onion_key_file, 'w') as kf: kf.write(f"{response.private_key_type}:{response.private_key}")
                self.my_onion_address = f"{response.service_id}.onion"
                self.is_tor_ready = True
                on_ready(self.my_onion_address)
                while True: time.sleep(1)
        except Exception as e: on_error(str(e))

    def start_presence_checker(self, update_ui_callback):
        def loop():
            while True:
                if self.is_tor_ready:
                    conn = self.db._get_conn()
                    cursor = conn.cursor()
                    cursor.execute("SELECT onion FROM contacts")
                    addrs = [row[0] for row in cursor.fetchall()]
                    conn.close()
                    for addr in addrs:
                        threading.Thread(target=self._ping_node, args=(addr, update_ui_callback), daemon=True).start()
                time.sleep(15)
        threading.Thread(target=loop, daemon=True).start()

    def _ping_node(self, onion_address, callback):
        try:
            s = socks.socksocket()
            s.set_proxy(socks.SOCKS5, "127.0.0.1", self.config.socks_port)
            s.settimeout(10)
            s.connect((onion_address, 80))
            packet = {
                "type": "ping",
                "sender": self.my_onion_address,
                "dh_pub": self.config.get_dh_public_bytes().hex(),
                "timestamp": int(time.time())
            }
            s.sendall(json.dumps(packet).encode('utf-8'))
            s.close()
            self.online_statuses[onion_address] = True
        except: self.online_statuses[onion_address] = False
        callback()

    def derive_new_ratchet_key(self, onion_address, current_key):
        new_key_bytes = self.config.get_derived_ratchet_key(current_key, b"ratchet_step")
        self.session_keys[onion_address] = (AESGCM(new_key_bytes), new_key_bytes)
        return new_key_bytes

    def bersihkan_warning_sesi_lama(self):
        self.db.hapus_pesan_sistem_berstatus("!")

    def kirim_pesan(self, target_onion, pesan, msg_id, callback):
        def async_send():
            self.db.simpan_chat(target_onion, "Kamu", pesan, status="...", msg_id=msg_id)
            callback()
            cipher_tuple = self.get_contact_cipher(target_onion)
            is_p2p_encrypted = cipher_tuple is not None
            try:
                if is_p2p_encrypted:
                    cipher, key = cipher_tuple
                    p_bytes = bytearray(pesan.encode())
                    nonce = os.urandom(12)
                    ciphertext = cipher.encrypt(nonce, p_bytes, None)
                    konten_pesan = base64.b64encode(nonce + ciphertext).decode()
                    self.derive_new_ratchet_key(target_onion, key)
                    secure_zero(p_bytes)
                else: konten_pesan = pesan
                packet = {
                    "type": "chat",
                    "sender": self.my_onion_address,
                    "content": konten_pesan,
                    "p2p_encrypted": is_p2p_encrypted,
                    "dh_pub": self.config.get_dh_public_bytes().hex(),
                    "timestamp": int(time.time()),
                    "id": msg_id
                }
                s = socks.socksocket()
                s.set_proxy(socks.SOCKS5, "127.0.0.1", self.config.socks_port)
                s.settimeout(20)
                s.connect((target_onion, 80))
                s.sendall(json.dumps(packet).encode('utf-8'))
                s.close()
                self.db.update_status_pesan(target_onion, msg_id, "✓")
            except Exception: self.db.update_status_pesan(target_onion, msg_id, "✗")
            callback()
            gc.collect()
        threading.Thread(target=async_send, daemon=True).start()

    def listen_incoming(self, on_msg, on_receipt):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        found_port = False
        start_port = self.config.local_port
        for port in range(start_port, start_port + 100):
            try:
                server.bind(('127.0.0.1', port))
                self.config.local_port = port
                found_port = True
                break
            except OSError: continue
        if not found_port: return
        server.listen(15)
        while True:
            try:
                conn, _ = server.accept()
                raw_bytes = conn.recv(1024 * 1024)
                if raw_bytes:
                    try:
                        packet = json.loads(raw_bytes.decode('utf-8'))
                        if abs(int(time.time()) - packet.get("timestamp", 0)) > 300:
                            conn.close()
                            continue
                        sender = packet.get("sender")
                        if not sender: continue
                        if packet.get("type") == "ping":
                            self.online_statuses[sender] = True
                            on_receipt()
                        elif packet.get("type") == "chat":
                            if "dh_pub" in packet:
                                conn_db = self.db._get_conn()
                                cursor = conn_db.cursor()
                                cursor.execute("SELECT shared_dh_public FROM contacts WHERE onion=?", (sender,))
                                row = cursor.fetchone()
                                if row:
                                    if row[0] and row[0] != packet["dh_pub"]:
                                        cursor.execute("UPDATE contacts SET shared_dh_public=?, is_verified=0 WHERE onion=?", (packet["dh_pub"], sender))
                                        conn_db.commit()
                                        if sender in self.session_keys: del self.session_keys[sender]
                                    elif not row[0]:
                                        cursor.execute("UPDATE contacts SET shared_dh_public=? WHERE onion=?", (packet["dh_pub"], sender))
                                        conn_db.commit()
                                conn_db.close()
                            content = packet.get("content")
                            msg_id = packet.get("id")
                            if packet.get("p2p_encrypted"):
                                cipher_tuple = self.get_contact_cipher(sender)
                                if cipher_tuple:
                                    cipher, key = cipher_tuple
                                    raw_data = base64.b64decode(content)
                                    nonce, ct = raw_data[:12], raw_data[12:]
                                    dec_bytes = bytearray(cipher.decrypt(nonce, ct, None))
                                    content = dec_bytes.decode()
                                    self.derive_new_ratchet_key(sender, key)
                                    secure_zero(dec_bytes)
                                else: content = "[Decryption Failed]"
                            self.db.simpan_chat(sender, sender, content, "", msg_id=msg_id)
                            on_msg(sender, content)
                    except Exception: pass
                conn.close()
                gc.collect()
            except: pass