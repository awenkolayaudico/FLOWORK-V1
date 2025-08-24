#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\delete_item_module\processor.py
# JUMLAH BARIS : 133
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
class DeleteItemModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.logger("Module 'Delete File/Folder' initialized successfully.", "INFO")
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        path_mode = config.get('path_mode', 'manual')
        delete_mode = config.get('delete_mode', 'file')
        ignore_not_found = config.get('ignore_not_found', True)
        target_path = ""
        if path_mode == 'dynamic':
            path_var = config.get('path_variable')
            if not path_var:
                raise ValueError("Dynamic path variable is not set.")
            target_path = get_nested_value(payload, path_var)
        else:
            target_path = config.get('target_path')
        if not target_path:
            raise ValueError("Target path to delete cannot be empty.")
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        if not os.path.exists(target_path):
            if ignore_not_found:
                msg = f"Item at '{target_path}' not found, skipping as configured."
                self.logger(msg, "WARN")
                status_updater("Not Found, Skipped", "WARN")
                payload['data']['deleted_path'] = target_path
                return payload
            else:
                raise FileNotFoundError(f"Item to be deleted was not found at: {target_path}")
        if mode == 'SIMULATE':
            status_updater(f"Simulating: Delete '{target_path}'", "WARN")
            self.logger(f"SIMULATION: Would delete item at '{target_path}'.", "WARN")
            payload['data']['deleted_path'] = target_path
            return payload
        try:
            status_updater(f"Deleting...", "INFO")
            self.logger(f"Attempting to delete '{target_path}'...", "INFO")
            if delete_mode == 'file':
                if not os.path.isfile(target_path):
                    raise IsADirectoryError(f"Target is a folder, but mode is 'Delete File'. Use 'Delete Folder' mode. Path: {target_path}")
                os.remove(target_path)
                self.logger(f"File '{target_path}' deleted successfully.", "SUCCESS")
            elif delete_mode == 'folder':
                if not os.path.isdir(target_path):
                    raise NotADirectoryError(f"Target is a file, but mode is 'Delete Folder'. Use 'Delete File' mode. Path: {target_path}")
                shutil.rmtree(target_path)
                self.logger(f"Folder '{target_path}' and all its contents deleted successfully.", "SUCCESS")
            status_updater("Delete Complete", "SUCCESS")
            payload['data']['deleted_path'] = target_path
        except Exception as e:
            self.logger(f"Failed to delete item: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            raise e
        return payload
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_delete_title'))
        settings_frame.pack(fill="x", padx=5, pady=(5,0))
        mode_frame = ttk.Frame(settings_frame)
        mode_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(mode_frame, text=self.loc.get('delete_mode_label')).pack(side='left', padx=(0,10))
        delete_mode_var = StringVar(value=config.get('delete_mode', 'file'))
        created_vars['delete_mode'] = delete_mode_var
        path_label_var = StringVar()
        browse_button_ref = {}
        def _update_ui_for_mode():
            is_file_mode = delete_mode_var.get() == 'file'
            path_label_var.set(self.loc.get('target_path_file_label') if is_file_mode else self.loc.get('target_path_folder_label'))
            if 'button' in browse_button_ref:
                browse_button_ref['button'].config(command=lambda: created_vars['target_path'].set(filedialog.askopenfilename(title=self.loc.get('browse_file_title_delete')) or created_vars['target_path'].get()) if is_file_mode else created_vars['target_path'].set(filedialog.askdirectory(title=self.loc.get('browse_folder_title_delete')) or created_vars['target_path'].get()))
        ttk.Radiobutton(mode_frame, text=self.loc.get('delete_mode_file'), variable=delete_mode_var, value='file', command=_update_ui_for_mode).pack(side='left', padx=5)
        ttk.Radiobutton(mode_frame, text=self.loc.get('delete_mode_folder'), variable=delete_mode_var, value='folder', command=_update_ui_for_mode).pack(side='left', padx=5)
        path_source_frame = ttk.LabelFrame(settings_frame, text=self.loc.get('prop_path_source_title'))
        path_source_frame.pack(fill='x', expand=True, padx=5, pady=5)
        path_mode_var = StringVar(value=config.get('path_mode', 'manual'))
        created_vars['path_mode'] = path_mode_var
        manual_frame = ttk.Frame(path_source_frame)
        dynamic_frame = ttk.Frame(path_source_frame)
        def _toggle_path_mode():
            if path_mode_var.get() == 'manual':
                dynamic_frame.pack_forget()
                manual_frame.pack(fill='x', padx=5, pady=5)
            else:
                manual_frame.pack_forget()
                dynamic_frame.pack(fill='x', padx=5, pady=5)
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_manual'), variable=path_mode_var, value='manual', command=_toggle_path_mode).pack(anchor='w', padx=10, pady=(5,0))
        ttk.Radiobutton(path_source_frame, text=self.loc.get('prop_mode_dynamic'), variable=path_mode_var, value='dynamic', command=_toggle_path_mode).pack(anchor='w', padx=10)
        ttk.Label(manual_frame, textvariable=path_label_var).pack(anchor='w')
        manual_entry_frame = ttk.Frame(manual_frame)
        manual_entry_frame.pack(fill='x', expand=True, pady=(2,10))
        target_path_var = StringVar(value=config.get('target_path', ''))
        ttk.Entry(manual_entry_frame, textvariable=target_path_var).pack(side='left', fill='x', expand=True)
        created_vars['target_path'] = target_path_var
        browse_button = ttk.Button(manual_entry_frame, style="secondary.TButton")
        browse_button.pack(side='left', padx=(5,0))
        browse_button_ref['button'] = browse_button
        LabelledCombobox(parent=dynamic_frame, label_text=self.loc.get('prop_path_input_key_label'), variable=StringVar(value=config.get('path_variable', '')), values=list(available_vars.keys()))
        created_vars['path_variable'] = dynamic_frame.winfo_children()[0].winfo_children()[1]['textvariable']
        _update_ui_for_mode() # Set initial state
        _toggle_path_mode() # Set initial state
        ignore_var = BooleanVar(value=config.get('ignore_not_found', True))
        ttk.Checkbutton(settings_frame, text=self.loc.get('ignore_not_found_label'), variable=ignore_var).pack(anchor='w', padx=10, pady=(0,10))
        created_vars['ignore_not_found'] = ignore_var
        ttk.Separator(parent_frame).pack(fill='x', pady=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'File system operations are not previewed.'}]
    def get_dynamic_output_schema(self, config):
        return [{
            "name": "data.deleted_path",
            "type": "string",
            "description": "The path of the file or folder that was successfully deleted."
        }]
