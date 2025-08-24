#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\copy_file_module\processor.py
# JUMLAH BARIS : 145
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
class CopyFileModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.logger("Module 'Copy File/Folder' initialized successfully.", "INFO")
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
        copy_mode = config.get('copy_mode', 'file')
        try:
            source_path = self._get_path_from_config(payload, config, 'source')
            destination_path = self._get_path_from_config(payload, config, 'destination')
        except ValueError as e:
            status_updater(str(e), "ERROR")
            raise e
        if not source_path or not destination_path:
            raise ValueError("Source and destination paths must not be empty.")
        if mode == 'EXECUTE' and not os.path.exists(source_path):
             raise FileNotFoundError(f"Source item not found: {source_path}")
        try:
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            if copy_mode == 'file':
                overwrite = config.get('overwrite', False)
                if mode == 'EXECUTE' and not os.path.isfile(source_path):
                    raise FileNotFoundError(f"Source path is not a file: {source_path}")
                final_destination = os.path.join(destination_path, os.path.basename(source_path)) if os.path.isdir(destination_path) else destination_path
                if mode == 'SIMULATE':
                    status_updater(f"Simulating: Copy '{source_path}' to '{final_destination}'", "WARN")
                    payload['data']['destination_path'] = final_destination
                    return {"payload": payload, "output_name": "success"}
                if os.path.exists(final_destination) and not overwrite:
                    raise FileExistsError(f"Destination file exists and overwrite is disabled: {final_destination}")
                os.makedirs(os.path.dirname(final_destination), exist_ok=True)
                shutil.copy2(source_path, final_destination)
                status_updater("File Copy Complete", "SUCCESS")
                self.logger(f"File successfully copied to: {final_destination}", "SUCCESS")
                payload['data']['destination_path'] = final_destination
            elif copy_mode == 'folder':
                if mode == 'EXECUTE' and not os.path.isdir(source_path):
                    raise NotADirectoryError(f"Source path must be a folder for this mode: {source_path}")
                if mode == 'SIMULATE':
                    status_updater(f"Simulating: Copy contents of '{source_path}' to '{destination_path}'", "WARN")
                    payload['data']['destination_path'] = destination_path
                    return {"payload": payload, "output_name": "success"}
                shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
                status_updater("Folder Copy Complete (Overwrite All)", "SUCCESS")
                payload['data']['destination_path'] = destination_path
        except Exception as e:
            self.logger(f"Failed during copy operation: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            raise e
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_copy_title'))
        settings_frame.pack(fill="x", padx=5, pady=(5,0))
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(mode_frame, text=self.loc.get('copy_mode_label')).pack(side='left', padx=(0,10))
        copy_mode_var = StringVar(value=config.get('copy_mode', 'file'))
        created_vars['copy_mode'] = copy_mode_var
        source_path_label_var = StringVar() # For dynamic label text
        def _update_ui_for_mode():
            is_file_mode = copy_mode_var.get() == 'file'
            source_path_label_var.set(self.loc.get('source_path_file_label') if is_file_mode else self.loc.get('source_path_folder_label'))
            if is_file_mode:
                overwrite_check.pack(anchor='w', padx=10, pady=(0,10))
            else:
                overwrite_check.pack_forget()
        ttk.Radiobutton(mode_frame, text=self.loc.get('copy_mode_file'), variable=copy_mode_var, value='file', command=_update_ui_for_mode).pack(side='left', padx=5)
        ttk.Radiobutton(mode_frame, text=self.loc.get('copy_mode_folder'), variable=copy_mode_var, value='folder', command=_update_ui_for_mode).pack(side='left', padx=5)
        def create_path_frame(parent, title_key, path_type, label_var=None):
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
            if label_var:
                ttk.Label(manual_frame, textvariable=label_var).pack(anchor='w')
            manual_entry_frame = ttk.Frame(manual_frame)
            manual_entry_frame.pack(fill='x', expand=True)
            path_var = StringVar(value=config.get(f'{path_type}_path', ''))
            ttk.Entry(manual_entry_frame, textvariable=path_var).pack(side='left', fill='x', expand=True)
            browse_cmd = lambda: path_var.set(filedialog.askopenfilename() or path_var.get()) if copy_mode_var.get() == 'file' else path_var.set(filedialog.askdirectory() or path_var.get())
            ttk.Button(manual_entry_frame, text=self.loc.get('browse_file_button'), command=browse_cmd).pack(side='left', padx=5)
            created_vars[f'{path_type}_path'] = path_var
            path_var_key = StringVar(value=config.get(f'{path_type}_path_variable', ''))
            LabelledCombobox(parent=dynamic_frame, label_text=self.loc.get('prop_path_input_key_label'), variable=path_var_key, values=list(available_vars.keys()))
            created_vars[f'{path_type}_path_variable'] = path_var_key
            _toggle()
        create_path_frame(settings_frame, 'prop_path_source_title', 'source', label_var=source_path_label_var)
        create_path_frame(settings_frame, 'prop_dest_path_source_title', 'destination')
        options_frame = ttk.Frame(settings_frame)
        options_frame.pack(fill='x', padx=10, pady=5)
        created_vars['overwrite'] = BooleanVar(value=config.get('overwrite', False))
        overwrite_check = ttk.Checkbutton(options_frame, text=self.loc.get('overwrite_label'), variable=created_vars['overwrite'])
        _update_ui_for_mode()
        ttk.Separator(parent_frame).pack(fill='x', pady=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'File system operations are not previewed.'}]
    def get_dynamic_output_schema(self, config):
        return [{
            "name": "data.destination_path",
            "type": "string",
            "description": "The full path of the file or folder that was successfully copied."
        }]
