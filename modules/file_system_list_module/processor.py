#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\file_system_list_module\processor.py
# JUMLAH BARIS : 111
#######################################################################

import os
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
class FileSystemListModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        path_mode = config.get('path_mode', 'manual')
        item_type = config.get('item_type', 'files')
        target_path = ""
        if path_mode == 'manual':
            target_path = config.get('target_path', '')
        elif path_mode == 'dynamic':
            path_input_key = config.get('path_input_key', '')
            if not path_input_key:
                raise ValueError("Payload key for the path has not been selected for dynamic mode.")
            target_path = get_nested_value(payload, path_input_key)
        if not target_path or not os.path.isdir(target_path):
            error_msg = f"Invalid or non-existent directory path: {target_path}"
            self.logger(error_msg, "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        try:
            status_updater(f"Listing items in {target_path}...", "INFO")
            items = os.listdir(target_path)
            results = []
            for item in items:
                full_path = os.path.join(target_path, item)
                if item_type == 'files' and os.path.isfile(full_path):
                    results.append(item)
                elif item_type == 'directories' and os.path.isdir(full_path):
                    results.append(item)
                elif item_type == 'all':
                    results.append(item)
            if 'data' not in payload: payload['data'] = {}
            payload['data']['item_list'] = results
            status_updater(f"Found {len(results)} items.", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"Error listing items in '{target_path}': {e}", "ERROR")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        path_source_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_path_source_title'))
        path_source_frame.pack(fill='x', padx=5, pady=5)
        path_mode_var = StringVar(value=config.get('path_mode', 'manual'))
        created_vars['path_mode'] = path_mode_var
        manual_frame = ttk.Frame(path_source_frame)
        dynamic_frame = ttk.Frame(path_source_frame)
        def _toggle_mode_ui():
            if path_mode_var.get() == 'manual':
                dynamic_frame.pack_forget()
                manual_frame.pack(fill='x', padx=10, pady=5)
            else:
                manual_frame.pack_forget()
                dynamic_frame.pack(fill='x', padx=10, pady=5)
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_manual'), variable=path_mode_var, value='manual', command=_toggle_mode_ui).pack(anchor='w', padx=10, pady=(5,0))
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_dynamic'), variable=path_mode_var, value='dynamic', command=_toggle_mode_ui).pack(anchor='w', padx=10, pady=(0,5))
        ttk.Label(manual_frame, text=self.loc.get('prop_manual_path_label')).pack(anchor='w')
        manual_path_entry_frame = ttk.Frame(manual_frame)
        manual_path_entry_frame.pack(fill='x', expand=True)
        manual_path_var = StringVar(value=config.get('target_path', ''))
        ttk.Entry(manual_path_entry_frame, textvariable=manual_path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(manual_path_entry_frame, text=self.loc.get('prop_browse_button'), command=lambda: manual_path_var.set(filedialog.askdirectory() or manual_path_var.get())).pack(side='left', padx=5)
        created_vars['target_path'] = manual_path_var # Shared key for simplicity
        ttk.Label(dynamic_frame, text=self.loc.get('prop_path_input_key_label')).pack(anchor='w')
        path_key_var = StringVar(value=config.get('path_input_key', ''))
        ttk.Combobox(dynamic_frame, textvariable=path_key_var, values=list(available_vars.keys()), state="readonly").pack(fill='x')
        created_vars['path_input_key'] = path_key_var
        _toggle_mode_ui()
        item_type_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_item_type_label'))
        item_type_frame.pack(fill='x', padx=5, pady=5)
        item_type_var = StringVar(value=config.get('item_type', 'files'))
        created_vars['item_type'] = item_type_var
        ttk.Radiobutton(item_type_frame, text=self.loc.get('item_type_files'), variable=item_type_var, value='files').pack(anchor='w', padx=10)
        ttk.Radiobutton(item_type_frame, text=self.loc.get('item_type_dirs'), variable=item_type_var, value='directories').pack(anchor='w', padx=10)
        ttk.Radiobutton(item_type_frame, text=self.loc.get('item_type_all'), variable=item_type_var, value='all').pack(anchor='w', padx=10, pady=(0,5))
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        path = config.get('target_path', '.')
        if not os.path.isdir(path):
            return [{'error': f"Path '{path}' not found or is not a directory."}]
        try:
            items = os.listdir(path)[:5] # Preview up to 5 items
            return [{'item_name': item} for item in items]
        except Exception as e:
            return [{'error': str(e)}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.item_list",
                "type": "list",
                "description": "A list of item names found in the target path."
            }
        ]
