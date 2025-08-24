#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\license_manager_service\license_manager_service.py
# JUMLAH BARIS : 236
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
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from flowork_kernel.kernel import Kernel
try:
    from cryptography.hazmat.primitives import hashes as crypto_hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.exceptions import InvalidSignature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
class LicenseManagerService(BaseService):
    LICENSE_PUBLIC_KEY_PEM_STRING = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAysqZG2+F82W0TgLHmF3Y
0GRPEZvXvmndTY84N/wA1ljt+JxMBVsmcVTkv8f1TrmFRD19IDzl2Yzb2lgqEbEy
GFxHhudC28leDsVEIp8B+oYWVm8Mh242YKYK8r5DAvr9CPQivnIjZ4BWgKKddMTd
harVxLF2CoSoTs00xWKd6VlXfoW9wdBvoDVifL+hCMepgLLdQQE4HbamPDJ3bpra
pCgcAD5urmVoJEUJdjd+Iic27RBK7jD1dWDO2MASMh/0IyXyM8i7RDymQ88gZier
U0OdWzeCWGyl4EquvR8lj5GNz4vg2f+oEY7h9AIC1f4ARtoihc+apSntqz7nAqa/
sQIDAQAB
-----END PUBLIC KEY-----"""
    REMOTE_CONFIG_PUBLIC_KEY_PEM_STRING = """-----BEGIN PUBLIC KEY-----
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
    REMOTE_TIER_CONFIG_URL = "https://raw.githubusercontent.com/awenkolayaudico/INFOUPDATE/refs/heads/main/flowork_tier_config.json"
    REMOTE_TIER_SIGNATURE_URL = "https://raw.githubusercontent.com/awenkolayaudico/INFOUPDATE/refs/heads/main/flowork_tier_config.sig"
    def __init__(self, kernel: 'Kernel', service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.license_public_key = None
        self.config_public_key = None # (PENAMBAHAN)
        self.license_data = {}
        self.is_local_license_valid = False
        self.server_error = None
        self.remote_permission_rules = None
        self._load_public_keys()
    def _fetch_remote_tier_config(self):
        """
        [MODIFIED] Fetches and digitally verifies the remote config.
        Defaults to monetization=TRUE if any step fails.
        """
        try:
            self.logger("LicenseManager: Fetching remote tier configuration and signature...", "INFO")
            config_response = requests.get(self.REMOTE_TIER_CONFIG_URL, timeout=10)
            config_response.raise_for_status()
            config_content_bytes = config_response.content
            sig_response = requests.get(self.REMOTE_TIER_SIGNATURE_URL, timeout=10)
            sig_response.raise_for_status()
            signature_b64 = sig_response.text.strip()
            if not self.config_public_key:
                raise SignatureVerificationError("Config public key is not loaded. Cannot verify remote config.")
            signature_bytes = base64.b64decode(signature_b64)
            self.config_public_key.verify(
                signature_bytes,
                config_content_bytes,
                padding.PKCS1v15(),
                crypto_hashes.SHA256()
            )
            self.remote_permission_rules = json.loads(config_content_bytes)
            self.logger("LicenseManager: Remote tier configuration loaded and signature VERIFIED successfully.", "SUCCESS")
            return True
        except (requests.exceptions.RequestException, InvalidSignature, SignatureVerificationError, json.JSONDecodeError) as e:
            self.logger(f"LicenseManager: CRITICAL: Could not fetch or verify remote config: {e}. Defaulting to SECURE mode (Monetization ON).", "CRITICAL")
            self.remote_permission_rules = {"monetization_active": True}
            return False
    def verify_license_on_startup(self):
        self.logger("LicenseManager: Starting license verification process V3 (Local First)...", "INFO")
        local_data = self._verify_local_license_file()
        if local_data:
            self.is_local_license_valid = True
            self.license_data = local_data
            self.logger("Local license file found and is valid.", "INFO")
        else:
            self.is_local_license_valid = False
            self.logger("No valid local license file found.", "INFO")
        self._fetch_remote_tier_config()
        monetization_is_active = self.remote_permission_rules and self.remote_permission_rules.get("monetization_active", False)
        if not monetization_is_active:
            override_tier = self.remote_permission_rules.get("default_tier_override", "architect") if self.remote_permission_rules else "architect"
            self.kernel.is_premium = True
            self.kernel.license_tier = override_tier
            self.logger(f"Monetization is INACTIVE. Granting full access with tier: '{override_tier}'.", "WARN")
            return
        self.logger("Monetization is ACTIVE. Proceeding with standard license verification.", "INFO")
        if not self.is_local_license_valid:
            self.logger("Monetization is active but no local license found. App will run in free mode.", "WARN")
            self.kernel.is_premium = False
            self.kernel.license_tier = "free"
            return
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
    def _load_public_keys(self):
        """ (MODIFIED) Loads ALL public keys needed by the service. """
        if not CRYPTO_AVAILABLE:
            self.logger("Cryptography library not found. Security features will be disabled.", "CRITICAL")
            return
        try:
            pem_data = self.LICENSE_PUBLIC_KEY_PEM_STRING.strip().encode('utf-8')
            self.license_public_key = serialization.load_pem_public_key(pem_data)
            self.logger("Public key for license verification loaded successfully.", "SUCCESS")
        except Exception as e:
            self.license_public_key = None
            self.logger(f"Failed to load license public key: {e}. License verification will fail.", "ERROR")
        try:
            pem_data = self.REMOTE_CONFIG_PUBLIC_KEY_PEM_STRING.strip().encode('utf-8')
            self.config_public_key = serialization.load_pem_public_key(pem_data)
            self.logger("Public key for remote config verification loaded successfully.", "SUCCESS")
        except Exception as e:
            self.config_public_key = None
            self.logger(f"Failed to load remote config public key: {e}. Remote config verification will fail.", "ERROR")
    def _get_machine_id(self) -> str:
        try:
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8 * 6, 8)][::-1])
            machine_id = hashlib.sha256(mac.encode()).hexdigest()
            self.logger(f"Generated Machine ID: {machine_id[:12]}...", "DEBUG")
            return machine_id
        except Exception as e:
            self.logger(f"Could not generate machine ID: {e}. Using a fallback ID.", "WARN")
            return hashlib.sha256("fallback_flowork_synapse_id".encode()).hexdigest()
    def _get_license_file_path(self):
        return os.path.join(self.kernel.data_path, self.LICENSE_FILE_NAME)
    def _verify_local_license_file(self):
        if not self.license_public_key: return None
        license_path = self._get_license_file_path()
        if not os.path.exists(license_path): return None
        try:
            with open(license_path, 'r', encoding='utf-8') as f: content = json.load(f)
            data_to_verify = content.get('data'); signature_b64 = content.get('signature')
            if not data_to_verify or not signature_b64: return None
            data_bytes = json.dumps(data_to_verify, separators=(',', ':')).encode('utf-8')
            signature_bytes = base64.b64decode(signature_b64)
            self.license_public_key.verify(signature_bytes, data_bytes, padding.PKCS1v15(), crypto_hashes.SHA256())
            return data_to_verify
        except Exception as e:
            self.logger(f"CRITICAL: License file tampered with or invalid. Deleting it. Error: {e}", "CRITICAL")
            try:
                os.remove(license_path)
            except OSError:
                pass
            return None
    def _verify_with_server(self):
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
        try:
            with open(file_path, 'r', encoding='utf-8') as f: content = json.load(f)
            data_to_verify = content.get('data')
            signature_bytes = base64.b64decode(content.get('signature'))
            data_bytes = json.dumps(data_to_verify, separators=(',', ':')).encode('utf-8')
            self.license_public_key.verify(signature_bytes, data_bytes, padding.PKCS1v15(), crypto_hashes.SHA256())
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
