#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\code_runner_module\processor.py
# JUMLAH BARIS : 145
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI
import ttkbootstrap as ttk
from tkinter import scrolledtext, StringVar
from flowork_kernel.api_contract import IDataPreviewer
import os
import json
import subprocess
import tempfile
from flowork_kernel.ui_shell import shared_properties
class CodeRunnerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    """
    Executes scripts from various languages using dynamic runner profiles.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.runners_path = os.path.join(self.kernel.project_root_path, "flowork_kernel", "core_runners")
        self.available_runners = {}
        self._load_runner_profiles()
    def _load_runner_profiles(self):
        """
        Scans the data/runners directory to dynamically find available languages.
        """
        if not os.path.isdir(self.runners_path):
            self.logger(f"Runner profiles directory not found: '{self.runners_path}'", "ERROR")
            return
        for filename in os.listdir(self.runners_path):
            if filename.endswith(".json"):
                runner_id = os.path.splitext(filename)[0]
                filepath = os.path.join(self.runners_path, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        self.available_runners[runner_id] = json.load(f)
                except Exception as e:
                    self.logger(f"Failed to load runner profile '{filename}': {e}", "ERROR")
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE') -> dict:
        language = config.get('language')
        code = config.get('code', '')
        if not language or language not in self.available_runners:
            error_msg = f"Language '{language}' is not selected or its runner profile was not found."
            status_updater(error_msg, "ERROR")
            if not isinstance(payload, dict): payload = {'data': {}}
            if 'data' not in payload: payload['data'] = {}
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        runner_profile = self.available_runners[language]
        status_updater(f"Executing {runner_profile.get('language_name', language)} script...", "INFO")
        temp_file_path = ''
        try:
            with tempfile.NamedTemporaryFile(mode='w+', suffix=runner_profile.get('file_extension', '.tmp'), delete=False, encoding='utf-8') as temp_file:
                temp_file_path = temp_file.name
                temp_file.write(code)
            command = [runner_profile.get('command'), temp_file_path]
            payload_as_string = json.dumps(payload)
            result = subprocess.run(
                command,
                input=payload_as_string,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=60
            )
            if not isinstance(payload, dict): payload = {'data': {}}
            if 'data' not in payload: payload['data'] = {}
            if result.returncode == 0:
                status_updater("Execution successful", "SUCCESS")
                payload['data']['code_output'] = result.stdout.strip()
                return {"payload": payload, "output_name": "success"}
            else:
                error_output = result.stderr.strip()
                status_updater("Execution failed", "ERROR")
                self.logger(f"Execution error in {language}: {error_output}", "ERROR")
                payload['error'] = error_output
                return {"payload": payload, "output_name": "error"}
        except FileNotFoundError:
            error_msg = f"Command '{runner_profile.get('command')}' not found. Ensure {runner_profile.get('language_name', language)} is installed and in your system's PATH."
            status_updater(error_msg, "ERROR")
            self.logger(error_msg, "ERROR")
            if not isinstance(payload, dict): payload = {'data': {}}
            if 'data' not in payload: payload['data'] = {}
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        except Exception as e:
            status_updater(f"Error: {e}", "ERROR")
            self.logger(f"An unexpected error occurred: {e}", "ERROR")
            if not isinstance(payload, dict): payload = {'data': {}}
            if 'data' not in payload: payload['data'] = {}
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
        finally:
            if temp_file_path and os.path.exists(temp_file_path):
                os.remove(temp_file_path)
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        property_vars = {}
        current_config = get_current_config()
        ttk.Label(parent_frame, text=self.loc.get('prop_language_label', fallback="Programming Language:")).pack(fill='x', padx=5, pady=(10,0))
        language_var = StringVar(value=current_config.get('language', 'python'))
        property_vars['language'] = language_var
        self.display_to_id_map = {runner.get('language_name', runner_id): runner_id for runner_id, runner in self.available_runners.items()}
        lang_combo = ttk.Combobox(parent_frame, textvariable=language_var, values=list(self.display_to_id_map.keys()), state="readonly")
        id_to_display_map = {v: k for k, v in self.display_to_id_map.items()}
        current_display_name = id_to_display_map.get(current_config.get('language', 'python'))
        if current_display_name:
            language_var.set(current_display_name)
        lang_combo.pack(fill='x', padx=5, pady=(0, 10))
        ttk.Label(parent_frame, text=self.loc.get('prop_code_label', fallback="Code to execute:")).pack(fill='x', padx=5, pady=(5,0))
        code_editor = scrolledtext.ScrolledText(parent_frame, height=15, font=("Consolas", 10))
        code_editor.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        code_editor.insert('1.0', current_config.get('code', ''))
        property_vars['code'] = code_editor
        original_language_var_get = language_var.get
        def get_language_id():
            display_name = original_language_var_get()
            return self.display_to_id_map.get(display_name, 'python')
        language_var.get = get_language_id
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, current_config, self.loc)
        property_vars.update(debug_vars)
        loop_vars = shared_properties.create_loop_settings_ui(parent_frame, current_config, self.loc, available_vars)
        property_vars.update(loop_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        """
        Previewing external code execution is complex and risky.
        Returning a placeholder is the safest approach.
        """
        return [{'status': 'preview_not_available', 'reason': 'External code execution is not safe to preview.'}]
    def get_dynamic_output_schema(self, config):
        """
        Declares the standard output of this module.
        """
        return [
            {
                "name": "data.code_output",
                "type": "string",
                "description": "The standard output (stdout) from the executed script."
            }
        ]
