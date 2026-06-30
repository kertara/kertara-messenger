import os
import secrets
import glob
import base64
import json
import socket
from argon2 import PasswordHasher
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives import serialization, hmac

class AppConfig:
    def __init__(self, user_profile=None):
        profile = user_profile if user_profile else "default"
        self.data_dir = os.path.abspath(f"./data_kertara_{profile}")
        os.makedirs(self.data_dir, exist_ok=True)
        self.tor_control_port = self._find_free_port()
        self.socks_port = self._find_free_port()
        self.local_port = self._find_free_port()
        self.tor_path = self._detect_tor_path()
        self.vault_meta_file = os.path.join(self.data_dir, "vault.meta")
        self.ph = PasswordHasher()
        self.cipher_suite = None
        self.master_exchange_key = None
        self.tor_data_dir = os.path.join(self.data_dir, "tor_state")
        self.onion_key_file = os.path.join(self.data_dir, "onion_private_key")
        self.dh_key_file = os.path.join(self.data_dir, "dh_private_key")
        os.makedirs(self.tor_data_dir, exist_ok=True)
        self._init_dh_keys()

    def initialize_vault(self, password):
        salt = secrets.token_bytes(16)
        hash_str = self.ph.hash(password)
        self.master_exchange_key = Fernet.generate_key() 
        with open(self.vault_meta_file, "wb") as f:
            f.write(salt)
            f.write(hash_str.encode())
            f.write(b"|")
            f.write(self.master_exchange_key)
        self._derive_master_key(password, salt)

    def unlock_vault(self, password):
        if not os.path.exists(self.vault_meta_file): return False
        with open(self.vault_meta_file, "rb") as f:
            content = f.read().split(b"|")
            salt = content[0][:16]
            stored_hash = content[0][16:].decode()
            self.master_exchange_key = content[1]
        try:
            self.ph.verify(stored_hash, password)
            self._derive_master_key(password, salt)
            return True
        except: return False

    def _derive_master_key(self, password, salt):
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher_suite = Fernet(key)
    
    def get_derived_ratchet_key(self, chain_key, constant_info=b"ratchet_step"):
        h = hmac.HMAC(chain_key, hashes.SHA256())
        h.update(constant_info)
        return h.finalize()

    def get_dh_fingerprint(self, pub_bytes):
        digest = hashes.Hash(hashes.SHA256())
        digest.update(pub_bytes)
        full_hash = digest.finalize()
        hex_hash = full_hash[:8].hex().upper()
        return "-".join([hex_hash[i:i+4] for i in range(0, 16, 4)])

    def _find_free_port(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _detect_tor_path(self):
        pola_folder = os.path.join(".", "tor-expert-bundle-windows-*")
        daftar_folder = glob.glob(pola_folder)
        if daftar_folder:
            folder_terdeteksi = daftar_folder[0]
            path_dinamis = os.path.join(folder_terdeteksi, "tor", "tor.exe")
            if os.path.exists(path_dinamis): return os.path.abspath(path_dinamis)
        return os.path.abspath(r".\tor\tor.exe")

    def _init_dh_keys(self):
        if not os.path.exists(self.dh_key_file):
            private_key = x25519.X25519PrivateKey.generate()
            priv_bytes = private_key.private_bytes(encoding=serialization.Encoding.Raw, format=serialization.PrivateFormat.Raw, encryption_algorithm=serialization.NoEncryption())
            with open(self.dh_key_file, "wb") as f: f.write(priv_bytes)

    def get_dh_private_key(self):
        with open(self.dh_key_file, "rb") as f: return x25519.X25519PrivateKey.from_private_bytes(f.read())

    def get_dh_public_bytes(self):
        priv = self.get_dh_private_key()
        pub = priv.public_key()
        return pub.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)

    @property
    def db_path(self): return os.path.join(self.data_dir, "chat_vault.db")

    def onion_to_krt(self, onion_address):
        if not onion_address or "onion" not in onion_address: return onion_address
        try:
            clean_address = onion_address.replace(".onion", "")
            encoded_bytes = base64.b32encode(clean_address.encode('utf-8'))
            encoded_string = encoded_bytes.decode('utf-8').replace("=", "")
            return f"KRT-{encoded_string}"
        except: return onion_address

    def krt_to_onion(self, krt_address):
        if not krt_address or not krt_address.startswith("KRT-"): return krt_address
        try:
            raw_encoded = krt_address.replace("KRT-", "")
            rem = len(raw_encoded) % 8
            if rem: raw_encoded += "=" * (8 - rem)
            decoded_bytes = base64.b32decode(raw_encoded.encode('utf-8'))
            decrypted_text = decoded_bytes.decode('utf-8')
            return f"{decrypted_text}.onion"
        except: return None

    def export_data_to_file(self, data_dict):
        cipher = Fernet(self.master_exchange_key)
        json_bytes = json.dumps(data_dict).encode('utf-8')
        return cipher.encrypt(json_bytes)

    def import_data_from_file(self, encrypted_bytes):
        cipher = Fernet(self.master_exchange_key)
        decrypted_json = cipher.decrypt(encrypted_bytes).decode('utf-8')
        return json.loads(decrypted_json)

    def get_my_fingerprint(self):
        my_pub_bytes = self.get_dh_public_bytes()
        return self.get_dh_fingerprint(my_pub_bytes)