#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\permission_manager_service\permission_manager_service.py
# JUMLAH BARIS : 97
#######################################################################

import os
import json
import base64
from ..base_service import BaseService
from flowork_kernel.exceptions import PermissionDeniedError
import hashlib
SIMULATED_DECRYPTION_KEY = b'flowork-capability-key-for-sim-32'
SIMULATED_PUBLIC_KEY = "flowork-simulated-public-key"
class PermissionManagerService(BaseService):
    """
    The central gatekeeper for all capability-based permissions.
    [REFACTORED V2] Now enters a secure fail-safe mode if rules cannot be loaded,
    denying all premium capabilities.
    [MODIFIED V3] Now responsible for generating the detailed permission denied message.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.permission_rules = {}
        self.is_compromised = False
        self.capability_display_map = {
            "web_scraping_advanced": "Advanced Web Scraping (Selenium)",
            "time_travel_debugger": "Time-Travel Debugger",
            "screen_recorder": "Screen Recorder",
            "unlimited_api": "Unlimited API & Webhooks",
            "preset_versioning": "Preset Version Management",
            "ai_provider_access": "AI Provider Access (Gemini, etc)",
            "ai_local_models": "Run Local AI Models (GGUF, etc)",
            "ai_copilot": "AI Co-pilot Analysis",
            "marketplace_upload": "Upload to Marketplace",
            "video_processing": "Advanced Video Processing",
            "ai_architect": "AI Architect (Workflow Generator)",
            "core_compiler": "Core Workflow Compiler",
            "module_generator": "Module Generator"
        }
        self._load_and_verify_rules()
    def _load_and_verify_rules(self):
        """
        Loads, verifies, and decrypts the permission rules at startup.
        This ensures the rules are tamper-proof and not human-readable.
        """
        self.logger("PermissionManager: Loading and verifying capability rules...", "INFO")
        rules_path = os.path.join(self.kernel.data_path, "permissions.bin")
        sig_path = os.path.join(self.kernel.data_path, "permissions.sig")
        if not os.path.exists(rules_path) or not os.path.exists(sig_path):
            self.logger("PermissionManager: 'permissions.bin' or '.sig' not found. Entering secure mode (all premium features denied).", "CRITICAL")
            self.is_compromised = True
            return
        try:
            with open(rules_path, 'rb') as f:
                encrypted_data = f.read()
            with open(sig_path, 'r', encoding='utf-8') as f:
                signature = f.read()
            hasher = hashlib.sha256()
            hasher.update(encrypted_data)
            hasher.update(SIMULATED_PUBLIC_KEY.encode('utf-8'))
            expected_signature = base64.b64encode(hasher.digest()).decode('utf-8')
            if signature != expected_signature:
                raise PermissionDeniedError("Permission file signature is invalid. The file may be tampered with.")
            self.logger("PermissionManager: Rules signature verified successfully.", "SUCCESS")
            decrypted_bytes = bytes([b ^ SIMULATED_DECRYPTION_KEY[i % len(SIMULATED_DECRYPTION_KEY)] for i, b in enumerate(encrypted_data)])
            decrypted_json = decrypted_bytes.decode('utf-8')
            self.permission_rules = json.loads(decrypted_json).get("capabilities", {})
            self.logger(f"PermissionManager: Loaded {len(self.permission_rules)} capability rules successfully.", "SUCCESS")
        except Exception as e:
            self.logger(f"PermissionManager: CRITICAL FAILURE loading permission rules: {e}. Entering secure mode (all premium features denied).", "CRITICAL")
            self.permission_rules = {}
            self.is_compromised = True
    def check_permission(self, capability: str, is_system_call: bool = False) -> bool:
        """
        Checks if the current user has the required tier for a specific capability.
        (MODIFIED) Now raises a detailed PermissionDeniedError on failure.
        """
        if is_system_call:
            return True
        if self.is_compromised:
            error_msg = self.loc.get('permission_denied_secure_mode', fallback="Access Denied due to secure mode. Please check license file signature.")
            raise PermissionDeniedError(error_msg)
        required_tier = self.permission_rules.get(capability)
        if not required_tier:
            return True
        user_tier = self.kernel.license_tier
        if not self.kernel.is_tier_sufficient(required_tier):
            capability_name = self.capability_display_map.get(capability, capability.replace('_', ' ').title())
            error_msg = self.loc.get('permission_denied_detailed',
                                     fallback="Access Denied. The '{capability}' feature requires a '{required_tier}' license, but your current tier is '{user_tier}'.",
                                     capability=capability_name, # FIXED: Changed 'capability_name' to 'capability' to match the JSON file and prevent errors.
                                     required_tier=required_tier.capitalize(),
                                     user_tier=user_tier.capitalize())
            raise PermissionDeniedError(error_msg)
        return True
