#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\json_file_handler_module\processor.py
# JUMLAH BARIS : 134
#######################################################################

import os
import json
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell import shared_properties
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
class JsonFileHandlerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        operation = config.get('operation', 'read')
        path_mode = config.get('path_mode', 'manual')
        file_path = ""
        if path_mode == 'dynamic':
            path_input_key = config.get('path_input_key', '')
            if not path_input_key:
                raise ValueError("Payload key for the file path has not been selected for dynamic mode.")
            file_path = get_nested_value(payload, path_input_key)
            self.logger(f"JSON Handler got dynamic path '{file_path}' from payload variable '{path_input_key}'", "DEBUG")
        else: # Default to manual
            file_path = config.get('file_path', '')
            self.logger(f"JSON Handler using static path: '{file_path}'", "DEBUG")
        if not file_path:
            error_msg = "File path is not specified or could not be found in payload."
            self.logger(error_msg, "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        try:
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            if operation == 'read':
                status_updater(f"Reading JSON from {os.path.basename(file_path)}...", "INFO")
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"File not found: {file_path}")
                with open(file_path, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                payload['data']['json_content'] = json_data
                status_updater("Read successful.", "SUCCESS")
            elif operation == 'write':
                status_updater(f"Writing JSON to {os.path.basename(file_path)}...", "INFO")
                data_var = config.get('data_variable_to_write')
                if not data_var:
                    raise ValueError("Data variable to write is not specified.")
                data_to_write = get_nested_value(payload, data_var)
                if data_to_write is None:
                    raise ValueError(f"Could not find data in payload at '{data_var}'.")
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data_to_write, f, indent=4)
                status_updater("Write successful.", "SUCCESS")
            payload['data']['file_path'] = file_path
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"JSON Handler error on '{file_path}': {e}", "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        op_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_operation_label', fallback="Operation"), padding=10)
        op_frame.pack(fill='x', padx=5, pady=5)
        op_var = StringVar(value=config.get('operation', 'read'))
        property_vars['operation'] = op_var
        path_source_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_path_source_title'))
        path_source_frame.pack(fill='x', padx=5, pady=5)
        path_mode_var = StringVar(value=config.get('path_mode', 'manual'))
        property_vars['path_mode'] = path_mode_var
        manual_frame = ttk.Frame(path_source_frame)
        dynamic_frame = ttk.Frame(path_source_frame)
        def _toggle_path_mode_ui():
            if path_mode_var.get() == 'manual':
                dynamic_frame.pack_forget()
                manual_frame.pack(fill='x', padx=10, pady=5)
            else:
                manual_frame.pack_forget()
                dynamic_frame.pack(fill='x', padx=10, pady=5)
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_manual'), variable=path_mode_var, value='manual', command=_toggle_path_mode_ui).pack(anchor='w', padx=10, pady=(5,0))
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_dynamic'), variable=path_mode_var, value='dynamic', command=_toggle_path_mode_ui).pack(anchor='w', padx=10, pady=(0,5))
        manual_path_var = StringVar(value=config.get('file_path', ''))
        property_vars['file_path'] = manual_path_var
        path_input_key_var = StringVar(value=config.get('source_variable', '')) # Renamed for clarity
        property_vars['source_variable'] = path_input_key_var
        data_var = StringVar(value=config.get('data_variable_to_write', ''))
        property_vars['data_variable_to_write'] = data_var
        ttk.Label(manual_frame, text=self.loc.get('prop_manual_path_label')).pack(anchor='w')
        manual_entry_frame = ttk.Frame(manual_frame)
        manual_entry_frame.pack(fill='x', expand=True)
        ttk.Entry(manual_entry_frame, textvariable=manual_path_var).pack(side='left', fill='x', expand=True)
        browse_button_manual = ttk.Button(manual_entry_frame, text=self.loc.get('prop_browse_button_read'))
        browse_button_manual.pack(side='left', padx=5)
        ttk.Label(dynamic_frame, text=self.loc.get('prop_path_input_key_label')).pack(anchor='w')
        ttk.Combobox(dynamic_frame, textvariable=path_input_key_var, values=list(available_vars.keys()), state="readonly").pack(fill='x')
        write_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_data_var_label'), padding=10)
        ttk.Combobox(write_frame, textvariable=data_var, values=list(available_vars.keys()), state="readonly").pack(fill='x', padx=5, pady=5)
        def toggle_ui_based_on_op(*args):
            if op_var.get() == 'read':
                write_frame.pack_forget()
                browse_button_manual.config(text=self.loc.get('prop_browse_button_read'), command=lambda: manual_path_var.set(filedialog.askopenfilename(filetypes=[("JSON files", "*.json")]) or manual_path_var.get()))
            else: # write
                write_frame.pack(fill='x', padx=5, pady=5)
                browse_button_manual.config(text=self.loc.get('prop_browse_button_write'), command=lambda: manual_path_var.set(filedialog.asksaveasfilename(filetypes=[("JSON files", "*.json")]) or manual_path_var.get()))
        ttk.Radiobutton(op_frame, text=self.loc.get('operation_read'), variable=op_var, value='read', command=toggle_ui_based_on_op).pack(side='left', padx=10)
        ttk.Radiobutton(op_frame, text=self.loc.get('operation_write'), variable=op_var, value='write', command=toggle_ui_based_on_op).pack(side='left', padx=10)
        _toggle_path_mode_ui()
        toggle_ui_based_on_op()
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        op = config.get('operation', 'read')
        path = config.get('file_path', 'N/A')
        return [{'operation': op, 'file_path': path, 'status': 'preview_not_available'}]
    def get_dynamic_output_schema(self, config):
        op = config.get('operation', 'read')
        schema = [{
            "name": "data.file_path", "type": "string",
            "description": "The full path of the file that was read or written to."
        }]
        if op == 'read':
            schema.append({
                "name": "data.json_content", "type": "object",
                "description": "The parsed JSON data from the file."
            })
        return schema
