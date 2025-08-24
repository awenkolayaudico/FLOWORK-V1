#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\file_system_actions_module\processor.py
# JUMLAH BARIS : 107
#######################################################################

import os
import shutil
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
class FileSystemActionsModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        action = config.get('action', 'delete')
        source_path = config.get('source_path')
        if not source_path or (mode == 'EXECUTE' and not self.kernel.file_system.exists(source_path, caller_module_id=self.module_id)):
            error_msg = f"Source path is invalid or does not exist: {source_path}"
            self.logger(error_msg, "ERROR")
            payload['error'] = error_msg
            return {"payload": payload, "output_name": "error"}
        try:
            if action == 'delete':
                status_updater(f"Deleting file {source_path}...", "INFO")
                if mode == 'EXECUTE':
                    self.kernel.file_system.remove(source_path, caller_module_id=self.module_id)
                status_updater("Delete successful.", "SUCCESS")
                if 'data' not in payload: payload['data'] = {}
                payload['data']['action_result'] = {'action': 'delete', 'path': source_path}
            elif action == 'copy':
                destination_path = config.get('destination_path')
                if not destination_path:
                    raise ValueError("Destination path for copy is not specified.")
                dest_dir = os.path.dirname(destination_path)
                if mode == 'EXECUTE' and not self.kernel.file_system.exists(dest_dir, caller_module_id=self.module_id):
                    os.makedirs(dest_dir, exist_ok=True) # Use os directly as it's a safe directory creation
                status_updater(f"Copying {source_path} to {destination_path}...", "INFO")
                if mode == 'EXECUTE':
                    shutil.copyfile(source_path, destination_path)
                status_updater("Copy successful.", "SUCCESS")
                if 'data' not in payload: payload['data'] = {}
                payload['data']['action_result'] = {'action': 'copy', 'source': source_path, 'destination': destination_path}
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"File Action '{action}' error: {e}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        action_var = StringVar(value=config.get('action', 'delete'))
        property_vars['action'] = action_var
        action_frame = ttk.Frame(parent_frame)
        action_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(action_frame, text=self.loc.get('prop_action_label', fallback="Action:")).pack(side='left', padx=(0,10))
        delete_rb = ttk.Radiobutton(action_frame, text=self.loc.get('action_delete', fallback="Delete"), variable=action_var, value='delete')
        delete_rb.pack(side='left')
        copy_rb = ttk.Radiobutton(action_frame, text=self.loc.get('action_copy', fallback="Copy"), variable=action_var, value='copy')
        copy_rb.pack(side='left', padx=10)
        source_path_var = StringVar(value=config.get('source_path', ''))
        property_vars['source_path'] = source_path_var
        source_frame = ttk.Frame(parent_frame)
        source_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(source_frame, text=self.loc.get('prop_source_path_label', fallback="Source Path:")).pack(anchor='w')
        source_entry_frame = ttk.Frame(source_frame)
        source_entry_frame.pack(fill='x', expand=True)
        ttk.Entry(source_entry_frame, textvariable=source_path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(source_entry_frame, text=self.loc.get('browse_button', fallback="Browse..."), command=lambda: source_path_var.set(filedialog.askopenfilename(title=self.loc.get('select_source_file')) or source_path_var.get())).pack(side='left', padx=5)
        dest_path_var = StringVar(value=config.get('destination_path', ''))
        property_vars['destination_path'] = dest_path_var
        dest_frame = ttk.Frame(parent_frame)
        dest_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(dest_frame, text=self.loc.get('prop_destination_path_label', fallback="Destination Path:")).pack(anchor='w')
        dest_entry_frame = ttk.Frame(dest_frame)
        dest_entry_frame.pack(fill='x', expand=True)
        ttk.Entry(dest_entry_frame, textvariable=dest_path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(dest_entry_frame, text=self.loc.get('browse_button', fallback="Browse..."), command=lambda: dest_path_var.set(filedialog.asksaveasfilename(title=self.loc.get('select_dest_file')) or dest_path_var.get())).pack(side='left', padx=5)
        def toggle_destination_visibility(*args):
            if action_var.get() == 'copy':
                dest_frame.pack(fill='x', padx=5, pady=5)
            else:
                dest_frame.pack_forget()
        action_var.trace_add('write', toggle_destination_visibility)
        toggle_destination_visibility() # Initial call
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        action = config.get('action', 'delete')
        source = config.get('source_path', 'N/A')
        dest = config.get('destination_path', 'N/A')
        if action == 'copy':
            return [{'action': 'copy', 'from': source, 'to': dest}]
        else:
            return [{'action': 'delete', 'target': source}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.action_result",
                "type": "object",
                "description": "A dictionary containing the results of the file operation."
            }
        ]
