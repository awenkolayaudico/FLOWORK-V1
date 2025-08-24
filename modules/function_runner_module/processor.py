#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\function_runner_module\processor.py
# JUMLAH BARIS : 95
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
import ttkbootstrap as ttk
from tkinter import scrolledtext
import traceback
import datetime
import json
import os
import importlib.util
from flowork_kernel.ui_shell import shared_properties
class FunctionRunnerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    """
    Executes a simple, user-provided Python script to manipulate the payload.
    [UPGRADE V5]: Added a safety net to handle non-dictionary payloads, preventing crashes.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE') -> dict:
        if not isinstance(payload, dict):
            self.logger("Received a non-dictionary payload. Wrapping it for compatibility.", "WARN") # MODIFIED: English Log
            original_payload_value = payload
            payload = {
                'data': {'previous_output': original_payload_value},
                'history': []
            }
        python_code = config.get('python_code', '')
        if not python_code.strip():
            status_updater("No code to run", "WARN") # MODIFIED: English Log
            return {"payload": payload, "output_name": "success"}
        status_updater("Executing custom code...", "INFO") # MODIFIED: English Log
        available_globals = {
            'datetime': datetime,
            'json': json,
            'os': os,
            'importlib': importlib.util
        }
        local_scope = {}
        indented_code = "\n".join([f"    {line}" for line in python_code.splitlines()])
        wrapped_function_code = f"""
def user_function(payload, log, kernel, args, json, os, importlib):
{indented_code}
"""
        try:
            exec(wrapped_function_code, available_globals, local_scope)
            script_to_run = local_scope['user_function']
            result = script_to_run(payload, self.logger, self.kernel, payload.get('data',{}).get('args', []), json, os, importlib.util)
            final_payload = payload if result is None else result
            status_updater("Execution successful", "SUCCESS") # MODIFIED: English Log
            return {"payload": final_payload, "output_name": "success"}
        except Exception as e:
            error_message = f"Error in custom Python code: {e}"
            full_traceback = traceback.format_exc()
            self.logger(f"{error_message}\n{full_traceback}", "ERROR") # MODIFIED: English Log
            status_updater("Execution failed", "ERROR") # MODIFIED: English Log
            if not isinstance(payload, dict):
                payload = {'data': {'original_payload': payload}}
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['error'] = error_message
            payload['data']['traceback'] = full_traceback
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        property_vars = {}
        current_config = get_current_config()
        vars_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_available_vars_label', fallback="Available Input Variables (Read-Only)"))
        vars_frame.pack(fill='x', padx=5, pady=(10, 5))
        vars_text = scrolledtext.ScrolledText(vars_frame, height=5, font=("Consolas", 9), wrap="word")
        vars_text.pack(fill="both", expand=True, padx=5, pady=5)
        vars_display_str = "# Your code can access these variables:\n# payload (dict): The entire data object\n# log (function): Call log('message', 'LEVEL')\n# kernel (object): Access kernel services\n# config (dict): This node's config values\n\n# Available keys inside 'payload':\n"
        vars_display_str += json.dumps(list(available_vars.keys()), indent=2)
        vars_text.insert('1.0', vars_display_str)
        vars_text.config(state="disabled")
        prop_info = next((p for p in self.manifest.get('properties', []) if p['id'] == 'python_code'), {})
        ttk.Label(parent_frame, text=self.loc.get('prop_python_code_label', fallback="Python Code to Execute:")).pack(fill='x', padx=5, pady=(10,0))
        code_editor = scrolledtext.ScrolledText(parent_frame, height=12, font=("Consolas", 10))
        code_editor.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        default_code = prop_info.get('default', '# Your code here')
        code_editor.insert('1.0', current_config.get('python_code', default_code))
        property_vars['python_code'] = code_editor
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, current_config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_dynamic_output_schema(self, config):
        return []
    def get_data_preview(self, config: dict):
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
