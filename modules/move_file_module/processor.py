#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\move_file_module\processor.py
# JUMLAH BARIS : 121
#######################################################################

import os
import shutil
import time
import random
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from tkinter import ttk, StringVar, BooleanVar, filedialog
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
class MoveFileModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.logger("Module 'Move File/Folder' initialized successfully.", "INFO")
    def _get_path_from_config(self, payload, config, path_type):
        """Helper to resolve path from either manual or dynamic config."""
        mode = config.get(f'{path_type}_path_mode', 'manual')
        if mode == 'dynamic':
            var_key = config.get(f'{path_type}_path_variable')
            if not var_key:
                raise ValueError(f"Dynamic path variable for '{path_type}' is not set.")
            return get_nested_value(payload, var_key)
        else: # manual
            return config.get(f'{path_type}_path')
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        try:
            source_path = self._get_path_from_config(payload, config, 'source')
            destination_path = self._get_path_from_config(payload, config, 'destination')
            overwrite = config.get('overwrite', False)
            if not source_path or not destination_path:
                raise ValueError("Source and destination paths must not be empty.")
            if mode == 'EXECUTE' and not os.path.exists(source_path):
                raise FileNotFoundError(f"Source file or folder not found at: {source_path}")
            final_path = os.path.join(destination_path, os.path.basename(source_path))
            if mode == 'SIMULATE':
                status_updater(f"Simulating: Move '{source_path}' to '{destination_path}'", "WARN")
                self.logger(f"SIMULATION: Would move '{source_path}' to '{destination_path}'.", "WARN")
                if 'data' not in payload: payload['data'] = {}
                payload['data']['new_path'] = final_path
                return payload
            status_updater(f"Moving...", "INFO")
            self.logger(f"Moving '{source_path}' to '{destination_path}'...", "INFO")
            if os.path.exists(final_path):
                if overwrite:
                    self.logger(f"Destination '{final_path}' already exists. Overwriting...", "WARN")
                    if os.path.isdir(final_path):
                        shutil.rmtree(final_path)
                    else:
                        os.remove(final_path)
                else:
                    raise FileExistsError(f"Destination path '{final_path}' already exists and overwrite is not enabled.")
            if not os.path.isdir(destination_path):
                 os.makedirs(destination_path, exist_ok=True)
            shutil.move(source_path, destination_path)
            status_updater("Move Complete", "SUCCESS")
            self.logger(f"Successfully moved. New location: {final_path}", "SUCCESS")
            if 'data' not in payload: payload['data'] = {}
            payload['data']['new_path'] = final_path
        except Exception as e:
            self.logger(f"Failed to move item: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            raise e
        return payload
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_move_title'))
        settings_frame.pack(fill="x", padx=5, pady=(5,0))
        def create_path_frame(parent, title_key, path_type):
            path_frame = ttk.LabelFrame(parent, text=self.loc.get(title_key))
            path_frame.pack(fill='x', expand=True, padx=5, pady=5)
            path_mode_var = StringVar(value=config.get(f'{path_type}_path_mode', 'manual'))
            created_vars[f'{path_type}_path_mode'] = path_mode_var
            manual_frame = ttk.Frame(path_frame)
            dynamic_frame = ttk.Frame(path_frame)
            def _toggle():
                if path_mode_var.get() == 'manual':
                    dynamic_frame.pack_forget()
                    manual_frame.pack(fill='x', padx=5, pady=5)
                else:
                    manual_frame.pack_forget()
                    dynamic_frame.pack(fill='x', padx=5, pady=5)
            ttk.Radiobutton(path_frame, text=self.loc.get('prop_mode_manual'), variable=path_mode_var, value='manual', command=_toggle).pack(anchor='w', padx=10, pady=(5,0))
            ttk.Radiobutton(path_frame, text=self.loc.get('prop_mode_dynamic'), variable=path_mode_var, value='dynamic', command=_toggle).pack(anchor='w', padx=10)
            manual_entry_frame = ttk.Frame(manual_frame)
            manual_entry_frame.pack(fill='x', expand=True)
            path_var = StringVar(value=config.get(f'{path_type}_path', ''))
            ttk.Entry(manual_entry_frame, textvariable=path_var).pack(side='left', fill='x', expand=True)
            browse_cmd = lambda: path_var.set(filedialog.askopenfilename() or path_var.get()) if config.get('move_mode') == 'file' else path_var.set(filedialog.askdirectory() or path_var.get())
            ttk.Button(manual_entry_frame, text=self.loc.get('prop_browse_button_read'), command=browse_cmd).pack(side='left', padx=5)
            created_vars[f'{path_type}_path'] = path_var
            path_var_key = StringVar(value=config.get(f'{path_type}_path_variable', ''))
            LabelledCombobox(parent=dynamic_frame, label_text=self.loc.get('prop_path_input_key_label'), variable=path_var_key, values=list(available_vars.keys()))
            created_vars[f'{path_type}_path_variable'] = path_var_key
            _toggle()
        create_path_frame(settings_frame, 'prop_path_source_title', 'source')
        create_path_frame(settings_frame, 'prop_dest_path_source_title', 'destination')
        overwrite_var = BooleanVar(value=config.get('overwrite', False))
        ttk.Checkbutton(settings_frame, text=self.loc.get('prop_move_overwrite_label'), variable=overwrite_var).pack(anchor='w', padx=15, pady=10)
        created_vars['overwrite'] = overwrite_var
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'File system operations are not previewed.'}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.new_path",
                "type": "string",
                "description": "The full path of the file or folder in its new location."
            }
        ]
