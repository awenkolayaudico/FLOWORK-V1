#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\community_addon_service\community_addon_service.py
# JUMLAH BARIS : 174
#######################################################################

import os
import tempfile
import zipfile
import shutil
import base64
import requests
import json
import uuid
from datetime import datetime, timedelta
from ..base_service import BaseService
class CommunityAddonService(BaseService):
    """
    Handles all interactions with the community addon repository on GitHub.
    This includes packaging, scanning, and uploading components.
    [MODIFIED V3] Now sends the user's license key for upload ownership validation.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.logger = self.kernel.write_to_log
        self.heroku_api_url = "https://flowork-addon-gate-ca4ad3903a88.herokuapp.com/"
        self.core_component_ids = self._load_core_component_ids()
    def _load_core_component_ids(self):
        core_ids = set()
        manifest_path = os.path.join(self.kernel.project_root_path, "core_integrity.json")
        try:
            with open(manifest_path, 'r', encoding='utf-8') as f:
                manifest_data = json.load(f)
            for path in manifest_data.keys():
                parts = path.split('/')
                if len(parts) > 1 and parts[0] in ['modules', 'plugins', 'widgets', 'triggers', 'ai_providers']:
                    core_ids.add(parts[1])
            self.logger(f"CommunityAddonService loaded {len(core_ids)} core component IDs for protection.", "INFO")
        except Exception as e:
            self.logger(f"CommunityAddonService could not load core component IDs: {e}", "WARN")
        return core_ids
    def _get_user_license_key(self):
        """
        A helper function to safely read the license key from the local license file.
        """
        license_file = os.path.join(self.kernel.data_path, "license.seal")
        if not os.path.exists(license_file):
            return None
        try:
            with open(license_file, 'r', encoding='utf-8') as f:
                license_content = json.load(f)
            return license_content.get('data', {}).get('license_key')
        except Exception as e:
            self.logger(f"Could not read license key from license.seal: {e}", "WARN")
            return None
    def upload_component(self, comp_type, component_id, description, tier):
        self.logger(f"CommunityAddonService: Starting upload for {comp_type} '{component_id}'...", "INFO")
        if not self.kernel.is_tier_sufficient('pro'):
            self.logger(f"Upload blocked for user with tier '{self.kernel.license_tier}'. Required: 'pro' or higher.", "WARN")
            return False, "You must have a 'Pro' tier license or higher to upload components."
        if component_id in self.core_component_ids:
            return False, self.loc.get('api_core_component_upload_error')
        user_license_key = self._get_user_license_key()
        if not user_license_key:
            return False, "Could not find a valid license key. Please ensure your license is active."
        manager_map = {
            "modules": "module_manager_service", "plugins": "module_manager_service",
            "widgets": "widget_manager_service", "triggers": "trigger_manager_service",
            "ai_providers": "ai_provider_manager_service", "presets": "preset_manager_service"
        }
        manager_service_name = manager_map.get(comp_type)
        if not manager_service_name:
            return False, f"Could not find a manager for component type '{comp_type}'."
        manager = self.kernel.get_service(manager_service_name)
        if not manager:
            return False, f"Manager service '{manager_service_name}' not found."
        manifest = {}
        component_path = None
        if comp_type == 'presets':
            component_path = os.path.join(self.kernel.data_path, "presets", f"{component_id}.json")
            manifest = {"name": component_id, "version": "1.0", "id": component_id}
        elif comp_type == 'ai_providers':
            component_path = os.path.join(self.kernel.ai_providers_path, component_id)
            provider_instance = manager.get_provider(component_id)
            if provider_instance and hasattr(provider_instance, 'get_manifest'):
                manifest = provider_instance.get_manifest()
            else:
                 return False, f"Could not retrieve manifest for AI provider '{component_id}'."
        else:
            loaded_components = getattr(manager, 'loaded_modules', getattr(manager, 'loaded_widgets', getattr(manager, 'loaded_triggers', {})))
            comp_data = loaded_components.get(component_id)
            if not comp_data or 'path' not in comp_data:
                return False, f"Could not find local path for component '{component_id}'."
            component_path = comp_data['path']
            manifest = comp_data.get("manifest", {})
        if not component_path or not (os.path.exists(component_path)):
            return False, f"Resolved component path does not exist: {component_path}"
        diagnostics_plugin = self.kernel.get_service("module_manager_service").get_instance("system_diagnostics_plugin")
        if not diagnostics_plugin:
            return False, "System Diagnostics plugin not found, cannot perform pre-flight scan."
        scan_successful, scan_report = diagnostics_plugin.scan_single_component_and_get_status(component_path)
        if not scan_successful:
            return False, f"Pre-upload scan failed:\n{scan_report}"
        self.logger(f"Pre-flight scan for '{component_id}' passed. Packaging and delegating to Heroku server...", "INFO")
        with tempfile.TemporaryDirectory() as temp_dir:
            zip_filename = f"{component_id}.zip"
            zip_path = os.path.join(temp_dir, zip_filename)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                if os.path.isdir(component_path):
                    for root, _, files in os.walk(component_path):
                        for file in files:
                            file_full_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_full_path, component_path)
                            zipf.write(file_full_path, arcname)
                else:
                    zipf.write(component_path, os.path.basename(component_path))
            try:
                upload_endpoint = f"{self.heroku_api_url.rstrip('/')}/upload-addon"
                form_data = {
                    "comp_type": comp_type,
                    "component_id": component_id,
                    "description": description,
                    "tier": tier,
                    "license_key": user_license_key
                }
                with open(zip_path, 'rb') as f:
                    files = {'file': (zip_filename, f, 'application/zip')}
                    response = requests.post(upload_endpoint, data=form_data, files=files, timeout=60)
                response.raise_for_status()
                response_json = response.json()
                self.logger(f"Heroku server response: {response_json.get('message')}", "SUCCESS")
                return True, response_json.get('message', "Upload successful!")
            except requests.exceptions.RequestException as e:
                error_message = f"Network error connecting to Heroku server: {e}"
                self.logger(error_message, "ERROR")
                return False, error_message
            except Exception as e:
                error_message = f"An unexpected error occurred during upload delegation: {e}"
                self.logger(error_message, "ERROR")
                return False, error_message
    def upload_model(self, model_filepath: str, model_id: str, description: str, tier: str):
        self.logger(f"CommunityAddonService: Starting upload for AI model '{model_id}'...", "INFO")
        if not self.kernel.is_tier_sufficient('pro'):
            return False, "You must have a 'Pro' tier license or higher to upload AI models."
        user_license_key = self._get_user_license_key()
        if not user_license_key:
            return False, "Could not find a valid license key. Please ensure your license is active."
        if not os.path.exists(model_filepath):
            return False, f"Model file to upload not found at: {model_filepath}"
        self.logger(f"Packaging model '{model_id}' and delegating to Heroku server...", "INFO")
        try:
            upload_endpoint = f"{self.heroku_api_url.rstrip('/')}/upload-model"
            form_data = {
                "model_id": model_id,
                "description": description,
                "tier": tier,
                "license_key": user_license_key
            }
            with open(model_filepath, 'rb') as f:
                files = {'file': (os.path.basename(model_filepath), f, 'application/octet-stream')}
                response = requests.post(upload_endpoint, data=form_data, files=files, timeout=600)
            response.raise_for_status()
            response_json = response.json()
            self.logger(f"Heroku server response for model upload: {response_json.get('message')}", "SUCCESS")
            return True, response_json.get('message', "Model upload successful!")
        except requests.exceptions.RequestException as e:
            error_message = f"Network error connecting to Heroku server for model upload: {e}"
            self.logger(error_message, "ERROR")
            return False, error_message
        except Exception as e:
            error_message = f"An unexpected error occurred during model upload delegation: {e}"
            self.logger(error_message, "ERROR")
            return False, error_message
