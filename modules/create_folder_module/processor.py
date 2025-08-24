#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\create_folder_module\processor.py
# JUMLAH BARIS : 122
#######################################################################

import os
import time
import random
import re
from flowork_kernel.api_contract import BaseModule
from tkinter import ttk, StringVar, BooleanVar, filedialog
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.api_contract import IDataPreviewer
class CreateFolderModule(BaseModule, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.logger("Modul 'Buat Folder' Cerdas berhasil diinisialisasi.", "INFO")
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        parent_path = config.get('parent_path')
        folder_name_mode = config.get('folder_name_mode', 'manual')
        create_parents = config.get('create_parents', True)
        if not parent_path:
            raise ValueError("Path folder induk tidak boleh kosong.")
        folder_name = ""
        if folder_name_mode == 'auto':
            variable_source = config.get('variable_source', '')
            if not variable_source:
                raise ValueError("Sumber variabel untuk nama folder otomatis belum dipilih.")
            folder_name = self.get_nested_value(payload, variable_source)
            if not folder_name or not isinstance(folder_name, str):
                raise ValueError(f"Nilai dari '{variable_source}' kosong atau bukan teks, tidak bisa dijadikan nama folder.")
            folder_name = re.sub(r'[\\/*?:"<>|]', "", folder_name)
            status_updater(f"Nama folder dari payload: '{folder_name}'", "INFO")
        else: # mode manual
            folder_name = config.get('manual_folder_name', '')
            if not folder_name:
                raise ValueError("Nama folder manual tidak boleh kosong.")
        final_path = os.path.join(parent_path, folder_name)
        if mode == 'SIMULATE':
            status_updater(f"Simulasi: Buat folder di '{final_path}'", "WARN")
            payload['created_path'] = final_path
            return payload
        try:
            self.logger(f"Mencoba membuat direktori di: {final_path}", "INFO")
            status_updater(f"Membuat: {folder_name}", "INFO")
            os.makedirs(final_path, exist_ok=create_parents)
            self.logger(f"Direktori '{final_path}' berhasil dibuat.", "SUCCESS")
            status_updater("Folder Dibuat", "SUCCESS")
            payload['created_path'] = final_path
        except OSError as e:
            error_msg = f"Gagal membuat direktori '{final_path}'. Error: {e}"
            self.logger(error_msg, "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            raise e
        return payload
    def get_nested_value(self, payload, key_path):
        """Helper untuk mengambil nilai dari nested dictionary di payload."""
        if not isinstance(key_path, str): return None
        keys = key_path.split('.')
        value = payload
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        return value
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_create_folder_title'))
        settings_frame.pack(fill="x", padx=5, pady=(5,0))
        path_frame = ttk.Frame(settings_frame)
        path_frame.pack(fill='x', padx=10, pady=5)
        ttk.Label(path_frame, text=self.loc.get('prop_parent_path_label')).pack(anchor='w')
        path_entry_frame = ttk.Frame(path_frame)
        path_entry_frame.pack(fill='x', expand=True)
        path_var = StringVar(value=config.get('parent_path', ''))
        ttk.Entry(path_entry_frame, textvariable=path_var).pack(side='left', fill='x', expand=True)
        created_vars['parent_path'] = path_var
        ttk.Button(path_entry_frame, text=self.loc.get('browse_folder_button'), style="secondary.TButton", command=lambda: path_var.set(filedialog.askdirectory(title=self.loc.get('browse_folder_title_dest')) or path_var.get())).pack(side='left', padx=(5,0))
        mode_frame = ttk.LabelFrame(settings_frame, text=self.loc.get('prop_foldername_mode_label'), padding=10)
        mode_frame.pack(fill='x', padx=10, pady=10)
        folder_name_mode_var = StringVar(value=config.get('folder_name_mode', 'manual'))
        created_vars['folder_name_mode'] = folder_name_mode_var
        auto_frame = ttk.Frame(mode_frame)
        manual_frame = ttk.Frame(mode_frame)
        def _toggle_mode_ui():
            if folder_name_mode_var.get() == 'auto':
                manual_frame.pack_forget()
                auto_frame.pack(fill='x')
            else:
                auto_frame.pack_forget()
                manual_frame.pack(fill='x')
        ttk.Radiobutton(mode_frame, text=self.loc.get('mode_auto_label'), variable=folder_name_mode_var, value='auto', command=_toggle_mode_ui).pack(anchor='w')
        ttk.Radiobutton(mode_frame, text=self.loc.get('mode_manual_label'), variable=folder_name_mode_var, value='manual', command=_toggle_mode_ui).pack(anchor='w')
        ttk.Label(auto_frame, text=self.loc.get('prop_variable_source_label')).pack(anchor='w', pady=(5,0))
        variable_source_var = StringVar(value=config.get('variable_source', ''))
        ttk.Combobox(auto_frame, textvariable=variable_source_var, values=list(available_vars.keys()), state="readonly").pack(fill='x')
        created_vars['variable_source'] = variable_source_var
        ttk.Label(manual_frame, text=self.loc.get('prop_manual_name_label')).pack(anchor='w', pady=(5,0))
        manual_folder_name_var = StringVar(value=config.get('manual_folder_name', ''))
        ttk.Entry(manual_frame, textvariable=manual_folder_name_var).pack(fill='x')
        created_vars['manual_folder_name'] = manual_folder_name_var
        _toggle_mode_ui()
        parents_var = BooleanVar(value=config.get('create_parents', True))
        ttk.Checkbutton(settings_frame, text=self.loc.get('create_parents_label'), variable=parents_var).pack(anchor='w', padx=10, pady=(0,10))
        created_vars['create_parents'] = parents_var
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        """
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        """
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
