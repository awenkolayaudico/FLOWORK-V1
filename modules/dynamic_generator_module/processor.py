#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\dynamic_generator_module\processor.py
# JUMLAH BARIS : 87
#######################################################################

import ttkbootstrap as ttk
from tkinter import IntVar, StringVar
from flowork_kernel.api_contract import BaseModule
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.api_contract import IDataPreviewer
class Processor(BaseModule, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        if hasattr(self, 'logger'):
            self.logger("Dynamic Node Generator v2.1 diinisialisasi.", "INFO")
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {} # Inisialisasi dictionary untuk menampung semua variabel UI
        settings_frame = ttk.LabelFrame(parent_frame, text="Pengaturan Generator")
        settings_frame.pack(fill="x", padx=5, pady=(10, 5))
        num_nodes_frame = ttk.Frame(settings_frame)
        num_nodes_frame.pack(fill='x', padx=10, pady=(5,10))
        ttk.Label(num_nodes_frame, text=self.loc.get('prop_label_num_nodes', fallback="Jumlah Node:")).pack(side='left')
        num_nodes_var = IntVar(value=config.get('num_nodes', 3))
        ttk.Entry(num_nodes_frame, textvariable=num_nodes_var, width=10).pack(side='left', padx=5)
        log_prefix_frame = ttk.Frame(settings_frame)
        log_prefix_frame.pack(fill='x', padx=10, pady=(0,10))
        ttk.Label(log_prefix_frame, text=self.loc.get('prop_label_log_prefix', fallback="Awalan Log:")).pack(side='left')
        log_prefix_var = StringVar(value=config.get('log_prefix', 'Log Dinamis'))
        ttk.Entry(log_prefix_frame, textvariable=log_prefix_var).pack(side='left', padx=5, fill='x', expand=True)
        connection_mode_frame = ttk.Frame(settings_frame)
        connection_mode_frame.pack(fill='x', padx=10, pady=(0,10))
        ttk.Label(connection_mode_frame, text=self.loc.get('prop_label_connection_mode', fallback="Mode Koneksi:")).pack(side='left')
        connection_mode_var = StringVar(value=config.get('connection_mode', self.loc.get('mode_chained')))
        ttk.Combobox(connection_mode_frame, textvariable=connection_mode_var, values=[self.loc.get('mode_chained'), self.loc.get('mode_parallel')], state='readonly').pack(side='left', padx=5)
        property_vars.update({
            'num_nodes': num_nodes_var,
            'log_prefix': log_prefix_var,
            'connection_mode': connection_mode_var
        })
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        loop_vars = shared_properties.create_loop_settings_ui(parent_frame, config, self.loc, available_vars)
        property_vars.update(loop_vars)
        return property_vars
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        num_nodes = config.get('num_nodes', 0)
        log_prefix = config.get('log_prefix', 'Log Dinamis')
        selected_mode_display = config.get('connection_mode', self.loc.get('mode_chained'))
        connection_mode = "parallel" if selected_mode_display == self.loc.get('mode_parallel') else "chained"
        self.logger(f"Akan membuat {num_nodes} node dinamis dalam mode '{connection_mode}'.", "INFO")
        nodes_to_create = []
        for i in range(num_nodes):
            node_name = f"{log_prefix} #{i + 1}"
            node_definition = {
                "name": node_name,
                "module_id": "set_variable_module",
                "config_values": {
                    "variables": [
                        { "var_name": f"status_dinamis_{i+1}", "var_value": f"Berhasil dieksekusi dari {node_name}", "var_type": "string" }
                    ]
                }
            }
            nodes_to_create.append(node_definition)
        return {
            "payload": payload,
            "output_name": "chain_output",
            "dynamic_nodes": {
                "nodes_to_create": nodes_to_create,
                "connection_details": {
                    "mode": connection_mode,
                    "connect_from_port": "chain_output"
                }
            }
        }
    def get_data_preview(self, config: dict):
        """
        TODO: Implement the data preview logic for this module.
        This method should return a small, representative sample of the data
        that the 'execute' method would produce.
        It should run quickly and have no side effects.
        """
        self.logger(f"'get_data_preview' is not yet implemented for {self.module_id}", 'WARN')
        return [{'status': 'preview not implemented'}]
