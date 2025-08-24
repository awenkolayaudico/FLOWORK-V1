#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\read_file_module\processor.py
# JUMLAH BARIS : 117
#######################################################################

import os
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell.shared_properties import create_debug_and_reliability_ui
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
class ReadFileModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Reads the content of a file. The path can be specified manually
    in the properties or dynamically from the payload.
    """
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        path_mode = config.get('path_mode', 'manual')
        output_key_name = config.get('output_key_name', 'file_content')
        encoding = config.get('encoding', 'utf-8')
        file_path = ""
        if path_mode == 'manual':
            file_path = config.get('manual_path')
            if not file_path:
                raise ValueError("File path has not been set in manual mode.")
        elif path_mode == 'dynamic':
            path_input_key = config.get('path_input_key')
            if not path_input_key:
                raise ValueError("The payload key for the file path has not been selected for dynamic mode.")
            from flowork_kernel.utils.payload_helper import get_nested_value
            file_path = get_nested_value(payload, path_input_key)
            if not file_path or not isinstance(file_path, str):
                status_updater(f"Path not found in payload key '{path_input_key}'", "ERROR")
                return {"payload": payload, "output_name": "on_failure"}
        if not os.path.exists(file_path):
            status_updater(f"File not found at: {file_path}", "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        if not os.path.isfile(file_path):
            status_updater(f"Path is a directory, not a file: {file_path}", "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        status_updater(f"Reading file: {os.path.basename(file_path)}", "INFO")
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data'][output_key_name] = content
            status_updater("File read successfully", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"Failed to read file '{file_path}': {e}", "ERROR")
            status_updater(f"Error reading file: {e}", "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        mode_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_path_source_title'))
        mode_frame.pack(fill='x', padx=5, pady=10)
        path_mode_var = StringVar(value=config.get('path_mode', 'manual'))
        created_vars['path_mode'] = path_mode_var
        manual_frame = ttk.Frame(mode_frame)
        dynamic_frame = ttk.Frame(mode_frame)
        def _toggle_mode_ui():
            if path_mode_var.get() == 'manual':
                dynamic_frame.pack_forget()
                manual_frame.pack(fill='x', padx=10, pady=5)
            else:
                manual_frame.pack_forget()
                dynamic_frame.pack(fill='x', padx=10, pady=5)
        ttk.Radiobutton(mode_frame, text=self.loc.get('prop_mode_manual'), variable=path_mode_var, value='manual', command=_toggle_mode_ui).pack(anchor='w', padx=10, pady=(5,0))
        ttk.Radiobutton(mode_frame, text=self.loc.get('prop_mode_dynamic'), variable=path_mode_var, value='dynamic', command=_toggle_mode_ui).pack(anchor='w', padx=10, pady=(0,5))
        ttk.Label(manual_frame, text=self.loc.get('prop_manual_path_label')).pack(anchor='w')
        manual_path_entry_frame = ttk.Frame(manual_frame)
        manual_path_entry_frame.pack(fill='x', expand=True, pady=(2, 5))
        manual_path_var = StringVar(value=config.get('manual_path', ''))
        ttk.Entry(manual_path_entry_frame, textvariable=manual_path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(manual_path_entry_frame, text=self.loc.get('prop_browse_button'), style="secondary.TButton", command=lambda: manual_path_var.set(filedialog.askopenfilename() or manual_path_var.get())).pack(side='left', padx=(5,0))
        created_vars['manual_path'] = manual_path_var
        ttk.Label(dynamic_frame, text=self.loc.get('prop_path_input_key_label')).pack(anchor='w')
        path_key_var = StringVar(value=config.get('path_input_key', ''))
        ttk.Combobox(dynamic_frame, textvariable=path_key_var, values=list(available_vars.keys()), state="readonly").pack(fill='x', pady=(2,5))
        created_vars['path_input_key'] = path_key_var
        _toggle_mode_ui()
        common_settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('read_file_prop_title'))
        common_settings_frame.pack(fill='x', padx=5, pady=0)
        ttk.Label(common_settings_frame, text=self.loc.get('prop_output_key_name_label')).pack(anchor='w', padx=10, pady=(5,0))
        output_key_var = StringVar(value=config.get('output_key_name', 'file_content'))
        ttk.Entry(common_settings_frame, textvariable=output_key_var).pack(fill='x', padx=10, pady=(0,10))
        created_vars['output_key_name'] = output_key_var
        ttk.Label(common_settings_frame, text=self.loc.get('prop_encoding_label')).pack(anchor='w', padx=10, pady=(5,0))
        encoding_var = StringVar(value=config.get('encoding', 'utf-8'))
        ttk.Combobox(common_settings_frame, textvariable=encoding_var, values=['utf-8', 'latin-1', 'ascii', 'utf-16']).pack(fill='x', padx=10, pady=(0,10))
        created_vars['encoding'] = encoding_var
        debug_vars = create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        path = config.get('manual_path', '')
        if not path or not os.path.exists(path):
            return [{'status': 'preview_not_available', 'reason': 'Manual path is not set or file does not exist.'}]
        try:
            with open(path, 'r', encoding=config.get('encoding', 'utf-8')) as f:
                content_preview = f.read(200) # Read first 200 chars
            return [{'file_content_preview': f"{content_preview}..."}]
        except Exception as e:
            return [{'error': str(e)}]
    def get_dynamic_output_schema(self, config):
        output_key = config.get('output_key_name', 'file_content')
        return [
            {
                "name": f"data.{output_key}",
                "type": "string",
                "description": "The entire content of the read file as a string."
            }
        ]
