#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\license_manager_service\license_manager_service.py
# JUMLAH BARIS : 197
#######################################################################

import os
import json
import base64
import uuid
import platform
import hashlib
import time
import datetime
import requests
import shutil
from tkinter import messagebox
from ..base_service import BaseService
from flowork_kernel.exceptions import SignatureVerificationError
from flowork_kernel.kernel import Kernel
try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
class LicenseManagerService(BaseService):
    """
    Manages all aspects of software licensing.
    This is the definitive version with all required methods.
    """
    PUBLIC_KEY_PEM_STRING = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAysqZG2+F82W0TgLHmF3Y
0GRPEZvXvmndTY84N/wA1ljt+JxMBVsmcVTkv8f1TrmFRD19IDzl2Yzb2lgqEbEy
GFxHhudC28leDsVEIp8B+oYWVm8Mh242YKYK8r5DAvr9CPQivnIjZ4BWgKKddMTd
harVxLF2CoSoTs00xWKd6VlXfoW9wdBvoDVifL+hCMepgLLdQQE4HbamPDJ3bpra
pCgcAD5urmVoJEUJdjd+Iic27RBK7jD1dWDO2MASMh/0IyXyM8i7RDymQ88gZier
U0OdWzeCWGyl4EquvR8lj5GNz4vg2f+oEY7h9AIC1f4ARtoihc+apSntqz7nAqa/
sQIDAQAB
-----END PUBLIC KEY-----"""
    LICENSE_FILE_NAME = "license.seal"
    HEROKU_API_URL = "https://flowork-addon-gate-ca4ad3903a88.herokuapp.com/"
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.public_key = None
        self.license_data = {}
        self.is_local_license_valid = False
        self.server_error = None
        self._load_public_key()
    def _load_public_key(self):
        """Loads the RSA public key from the hardcoded string."""
        if not CRYPTO_AVAILABLE:
            self.logger("Cryptography library not found. License features will be disabled.", "CRITICAL")
            return
        try:
            pem_data = self.PUBLIC_KEY_PEM_STRING.strip().encode('utf-8')
            self.public_key = serialization.load_pem_public_key(pem_data)
            self.logger("Public key for license verification loaded successfully.", "SUCCESS")
        except Exception as e:
            self.public_key = None
            self.logger(f"Failed to load public key: {e}. License verification will fail.", "ERROR")
    def _get_machine_id(self) -> str:
        """Generates a unique and consistent machine ID based on the MAC address."""
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
            machine_id = hashlib.sha256(mac.encode()).hexdigest()
            self.logger(f"Generated Machine ID: {machine_id[:12]}...", "DEBUG")
            return machine_id
        except Exception as e:
            self.logger(f"Could not generate machine ID: {e}. Using a fallback ID.", "WARN")
            return hashlib.sha256("fallback_flowork_synapse_id".encode()).hexdigest()
    def _get_license_file_path(self):
        """Constructs the full path to the license file."""
        return os.path.join(self.kernel.data_path, self.LICENSE_FILE_NAME)
    def verify_license_on_startup(self):
        """
        The main gatekeeper function called by StartupService.
        Performs a full validation chain: local file -> server.
        """
        self.logger("LicenseManager: Starting license verification process...", "INFO")
        local_data = self._verify_local_license_file()
        if not local_data:
            self.logger("Local license file not found or invalid. App will run in free mode.", "WARN")
            self.kernel.is_premium = False
            self.kernel.license_tier = "free"
            return
        self.is_local_license_valid = True
        self.license_data = local_data
        try:
            is_server_ok, server_message = self._verify_with_server()
            if is_server_ok:
                self.logger("Server verification successful. Premium mode activated.", "SUCCESS")
                self.kernel.is_premium = True
                self.kernel.license_tier = self.license_data.get('tier', 'basic')
            else:
                self.logger(f"Server verification failed: {server_message}. Running in free mode.", "ERROR")
                self.kernel.is_premium = False
                self.kernel.license_tier = "free"
                messagebox.showerror("License Error", f"License validation failed: {server_message}")
        except requests.exceptions.RequestException as e:
            self.logger(f"Could not connect to license server: {e}. Defaulting to FREE mode.", "ERROR")
            self.kernel.is_premium = False
            self.kernel.license_tier = "free"
            messagebox.showwarning("License Server Unreachable", "Could not connect to the license server. The application will run in FREE mode.")
    def _verify_local_license_file(self):
        """Verifies the digital signature of the local license.seal file."""
        if not self.public_key: return None
        license_path = self._get_license_file_path()
        if not os.path.exists(license_path): return None
        try:
            with open(license_path, 'r', encoding='utf-8') as f: content = json.load(f)
            data_to_verify = content.get('data'); signature_b64 = content.get('signature')
            if not data_to_verify or not signature_b64: return None
            data_bytes = json.dumps(data_to_verify, separators=(',', ':')).encode('utf-8')
            signature_bytes = base64.b64decode(signature_b64)
            self.public_key.verify(signature_bytes, data_bytes, padding.PKCS1v15(), crypto_hashes.SHA256())
            return data_to_verify
        except Exception as e:
            self.logger(f"CRITICAL: License file tampered with or invalid. Deleting it. Error: {e}", "CRITICAL")
            try:
                os.remove(license_path)
            except OSError:
                pass
            return None
    def _verify_with_server(self):
        """Checks the license status against the Heroku server."""
        expiry_date_str = self.license_data.get("expiry_date", "")
        if expiry_date_str and expiry_date_str != "never":
            try:
                expiry_date = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
                if datetime.date.today() > expiry_date:
                    return False, f"This license has expired on {expiry_date_str}."
            except ValueError:
                 self.logger(f"License has an invalid date format: {expiry_date_str}", "WARN")
        api_url = f"{self.HEROKU_API_URL}validate-license"
        payload = {"license_key": self.license_data.get('license_key'), "machine_id": self._get_machine_id()}
        response = requests.post(api_url, json=payload, timeout=15)
        if response.status_code == 200:
            return True, "License is valid."
        else:
            try:
                error_msg = response.json().get("error", "Unknown server error.")
            except json.JSONDecodeError:
                error_msg = f"Server returned non-JSON response (Status: {response.status_code})."
            return False, error_msg
    def activate_license_from_file(self, file_path: str):
        """Activates a new license using a .seal file provided by the user."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = json.load(f)
            data_to_verify = content.get('data')
            signature_bytes = base64.b64decode(content.get('signature'))
            data_bytes = json.dumps(data_to_verify, separators=(',', ':')).encode('utf-8')
            self.public_key.verify(signature_bytes, data_bytes, padding.PKCS1v15(), crypto_hashes.SHA256())
        except Exception:
            messagebox.showerror("Activation Failed", "The selected license file is not valid or has been tampered with.")
            return
        api_url = f"{self.HEROKU_API_URL}activate-license"
        payload = {"license_key": data_to_verify.get('license_key'), "machine_id": self._get_machine_id()}
        try:
            response = requests.post(api_url, json=payload, timeout=20)
            if response.status_code != 200: raise Exception(response.json().get("error", "Unknown activation error."))
            shutil.copyfile(file_path, self._get_license_file_path())
            messagebox.showinfo("Activation Successful", "License activated! The application will now restart.")
            self.kernel.get_service("event_bus").publish("RESTART_APP", {})
        except Exception as e:
            messagebox.showerror("Activation Failed", f"Could not activate license on server: {e}")
    def deactivate_license_on_server(self):
        """
        (PERBAIKAN) Deactivates the current license. Now returns a (success, message) tuple.
        It no longer shows popups directly.
        """
        if not self.is_local_license_valid:
            return False, "No active license found on this computer."
        api_url = f"{self.HEROKU_API_URL}deactivate-license"
        payload = {"license_key": self.license_data.get('license_key'), "machine_id": self._get_machine_id()}
        try:
            response = requests.post(api_url, json=payload, timeout=20)
            if response.status_code != 200:
                raise Exception(response.json().get("error", "Unknown deactivation error from server."))
            local_license_path = self._get_license_file_path()
            if os.path.exists(local_license_path):
                os.remove(local_license_path)
            return True, "License deactivated successfully. The application will now restart in free mode."
        except Exception as e:
            return False, f"An error occurred during deactivation: {e}"
    def check_for_updates(self):
        self.logger("check_for_updates() is deprecated and now handled by UpdateService.", "WARN")
        return None
    def verify_license(self):
        self.logger("verify_license() is deprecated and now handled by verify_license_on_startup().", "WARN")
        return "free"
    def activate_license_on_server(self, local_license_data: dict):
        self.logger("activate_license_on_server() is deprecated.", "WARN")
        return False, "This function is no longer in use."
