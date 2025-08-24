#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\flowork_kernel\services\widget_manager_service\widget_manager_service.py
# JUMLAH BARIS : 225
#######################################################################

import os
import json
import importlib.util
import py_compile
import subprocess
import sys
from importlib.machinery import ExtensionFileLoader
import importlib.metadata
from ..base_service import BaseService
import zipfile
import tempfile
import shutil
class WidgetManagerService(BaseService):
    """
    Manages the discovery, loading, and access to all custom dashboard widgets.
    [MODIFICATION] Implements hybrid loading: prioritizes locked native modules (.awenkaudico)
    and falls back to source .py files for open-source/development mode.
    """
    def __init__(self, kernel, service_id: str):
        super().__init__(kernel, service_id)
        self.widgets_dir = self.kernel.widgets_path
        self.loaded_widgets = {}
        self.paused_status_file = os.path.join(self.kernel.data_path, 'paused_widgets.json')
        self.cache_file = os.path.join(self.kernel.data_path, 'widget_index.cache')
        self.kernel.write_to_log("Service 'WidgetManager' initialized.", "DEBUG")
    def _is_cache_valid(self):
        if not os.path.exists(self.cache_file):
            return False
        cache_mod_time = os.path.getmtime(self.cache_file)
        if os.path.exists(self.widgets_dir):
            if os.path.getmtime(self.widgets_dir) > cache_mod_time:
                return False
            for root, dirs, _ in os.walk(self.widgets_dir):
                for d in dirs:
                    if os.path.getmtime(os.path.join(root, d)) > cache_mod_time:
                        return False
        return True
    def discover_and_load_widgets(self):
        self.kernel.write_to_log("WidgetManager: Starting discovery and loading of custom widgets...", "INFO")
        self.loaded_widgets.clear()
        paused_ids = self._load_paused_status()
        if self._is_cache_valid():
            self.kernel.write_to_log("WidgetManager: Valid cache found. Loading widgets from index...", "INFO")
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            for widget_id, widget_data in cached_data.items():
                self._process_single_widget(
                    widget_dir=widget_data['path'],
                    widget_id=widget_id,
                    paused_ids=paused_ids,
                    manifest_override=widget_data['manifest']
                )
            self.kernel.write_to_log(f"WidgetManager: Widget loading from cache complete. Total loaded: {len(self.loaded_widgets)}", "INFO")
            return
        self.kernel.write_to_log("WidgetManager: Cache not found or stale. Discovering from disk...", "WARN")
        discovered_data_for_cache = {}
        if not os.path.exists(self.widgets_dir):
            return
        for widget_id in os.listdir(self.widgets_dir):
            widget_dir = os.path.join(self.widgets_dir, widget_id)
            if os.path.isdir(widget_dir) and widget_id != '__pycache__':
                manifest = self._process_single_widget(widget_dir, widget_id, paused_ids)
                if manifest:
                    discovered_data_for_cache[widget_id] = {
                        'manifest': manifest,
                        'path': widget_dir
                    }
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(discovered_data_for_cache, f)
            self.kernel.write_to_log(f"WidgetManager: Widget index cache created at {self.cache_file}", "SUCCESS")
        except Exception as e:
            self.kernel.write_to_log(f"WidgetManager: Failed to write widget cache file: {e}", "ERROR")
        self.kernel.write_to_log(f"WidgetManager: Custom widget loading complete. Total loaded: {len(self.loaded_widgets)}", "INFO")
    def _process_single_widget(self, widget_dir, widget_id, paused_ids, manifest_override=None):
        self.kernel.write_to_log(f" -> Processing widget: '{widget_id}'", "DEBUG")
        manifest = manifest_override
        if manifest is None:
            manifest_path = os.path.join(widget_dir, "manifest.json")
            if not os.path.exists(manifest_path):
                return None
            try:
                with open(manifest_path, 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
            except Exception as e:
                self.kernel.write_to_log(f"   ! Failed to read manifest for widget '{widget_id}': {e}", "WARN")
                return None
        try:
            self._install_dependencies(widget_dir, manifest.get('name', widget_id))
            entry_point = manifest.get("entry_point")
            if not entry_point:
                raise ValueError("entry_point not found in manifest.json")
            module_filename, class_name = entry_point.split('.')
            source_file_path = os.path.join(widget_dir, f"{module_filename}.py")
            native_file_path = os.path.join(widget_dir, f"{module_filename}.awenkaudico")
            path_to_load = None
            is_native_module = False
            if os.path.exists(native_file_path):
                path_to_load = native_file_path
                is_native_module = True
                self.kernel.write_to_log(f"   -> Found locked native file for widget '{widget_id}'. Prioritizing it.", "DEBUG")
            elif os.path.exists(source_file_path):
                path_to_load = source_file_path
                is_native_module = False
                self.kernel.write_to_log(f"   -> Found source .py file for widget '{widget_id}'. Using it (Open-Source/Dev mode).", "DEBUG")
            if not path_to_load:
                self.kernel.write_to_log(f"   ! Failed: No source or protected file found for widget '{widget_id}'.", "ERROR")
                return manifest
            module_full_name = f"widgets.{widget_id}.{module_filename}"
            if is_native_module:
                loader = ExtensionFileLoader(module_full_name, path_to_load)
                spec = importlib.util.spec_from_loader(loader.name, loader)
            else:
                spec = importlib.util.spec_from_file_location(module_full_name, path_to_load)
            module_lib = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module_lib)
            widget_class = getattr(module_lib, class_name)
            self.loaded_widgets[widget_id] = {
                "class": widget_class,
                "name": manifest.get('name', widget_id),
                "manifest": manifest,
                "path": widget_dir,
                "is_paused": widget_id in paused_ids
            }
            self.kernel.write_to_log(f" + Success: Widget '{widget_id}' loaded.", "SUCCESS")
        except Exception as e:
            self.kernel.write_to_log(f" ! Failed to load widget '{widget_id}': {e}", "ERROR")
        return manifest
    def _install_dependencies(self, component_path, component_name):
        requirements_path = os.path.join(component_path, 'requirements.txt')
        if not os.path.exists(requirements_path): return
        try:
            with open(requirements_path, 'r', encoding='utf-8') as f:
                packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            for package in packages:
                package_name_for_check = package.split('==')[0].split('>=')[0].strip()
                try:
                    importlib.metadata.version(package_name_for_check)
                except importlib.metadata.PackageNotFoundError:
                    self.kernel.write_to_log(f"     - Dependency '{package}' for '{component_name}' not found. Installing...", "INFO")
                    try:
                        subprocess.check_call([sys.executable, "-m", "pip", "install", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except subprocess.CalledProcessError as e:
                        self.kernel.write_to_log(f"     ! FAILED to install '{package}'. Error: {e}", "ERROR")
                        raise e
        except Exception as e:
            self.kernel.write_to_log(f"     ! FAILED to process requirements.txt for '{component_name}'. Error: {e}", "ERROR")
            raise e
    def _load_paused_status(self):
        if os.path.exists(self.paused_status_file):
            try:
                with open(self.paused_status_file, 'r') as f: return json.load(f)
            except (json.JSONDecodeError, IOError): return []
        return []
    def _save_paused_status(self):
        paused_ids = [wid for wid, data in self.loaded_widgets.items() if data.get("is_paused")]
        try:
            with open(self.paused_status_file, 'w') as f: json.dump(paused_ids, f, indent=4)
        except IOError as e:
            self.kernel.write_to_log(f" ! Failed to save widget paused status: {e}", "ERROR")
    def set_widget_paused(self, widget_id, is_paused):
        if widget_id in self.loaded_widgets:
            self.loaded_widgets[widget_id]["is_paused"] = is_paused
            self._save_paused_status()
            if self.kernel.root:
                self.kernel.root.refresh_ui_components()
            return True
        return False
    def install_component(self, zip_filepath: str) -> (bool, str):
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                with zipfile.ZipFile(zip_filepath, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                component_root_path = None
                if os.path.exists(os.path.join(temp_dir, 'manifest.json')):
                    component_root_path = temp_dir
                else:
                    dir_items = [d for d in os.listdir(temp_dir) if os.path.isdir(os.path.join(temp_dir, d))]
                    if len(dir_items) == 1:
                        potential_path = os.path.join(temp_dir, dir_items[0])
                        if os.path.exists(os.path.join(potential_path, 'manifest.json')):
                            component_root_path = potential_path
                if not component_root_path:
                    return False, "manifest.json not found in the root of the zip archive or in a single subdirectory."
                with open(os.path.join(component_root_path, 'manifest.json'), 'r', encoding='utf-8') as f:
                    manifest = json.load(f)
                required_tier = manifest.get('tier', 'free')
                if not self.kernel.is_tier_sufficient(required_tier):
                    error_msg = f"Installation failed. This widget requires a '{required_tier.capitalize()}' license or higher. Your current tier is '{self.kernel.license_tier.capitalize()}'."
                    self.kernel.write_to_log(error_msg, "ERROR")
                    return False, error_msg
                component_id = manifest.get('id')
                if not component_id:
                    return False, "Component 'id' is missing from manifest.json."
                final_path = os.path.join(self.widgets_dir, component_id)
                if os.path.exists(final_path):
                    return False, f"Widget '{component_id}' is already installed."
                shutil.move(component_root_path, final_path)
                self.kernel.write_to_log(f"Widget '{component_id}' installed successfully.", "SUCCESS")
                return True, f"Widget '{manifest.get('name', component_id)}' installed successfully."
            except Exception as e:
                self.kernel.write_to_log(f"Widget installation failed: {e}", "ERROR")
                return False, f"An error occurred during widget installation: {e}"
    def uninstall_component(self, component_id: str) -> (bool, str):
        if component_id not in self.loaded_widgets:
            return False, f"Widget '{component_id}' is not currently loaded or does not exist."
        component_data = self.loaded_widgets[component_id]
        component_path = component_data.get('path')
        if not component_path or not os.path.isdir(component_path):
            return False, f"Path for widget '{component_id}' not found or is invalid."
        try:
            shutil.rmtree(component_path)
            del self.loaded_widgets[component_id]
            self.kernel.write_to_log(f"Widget '{component_id}' folder deleted successfully.", "SUCCESS")
            return True, f"Widget '{component_id}' uninstalled. A restart is required to fully clear it."
        except Exception as e:
            self.kernel.write_to_log(f"Failed to delete widget folder '{component_path}': {e}", "ERROR")
            return False, f"Could not delete widget folder: {e}"
