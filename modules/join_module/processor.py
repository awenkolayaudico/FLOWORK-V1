#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\join_module\processor.py
# JUMLAH BARIS : 85
#######################################################################

import json
import threading
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
import ttkbootstrap as ttk
from tkinter import IntVar
class Processor(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Processor for the Join module. Waits for all inputs before continuing.
    [REFACTORED] Updated to align with modern architecture, including interfaces,
    safer payload merging, and full localization.
    """
    TIER = "free"
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
        self.lock = threading.Lock()
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        node_instance_id = config.get('__internal_node_id')
        if not node_instance_id:
            error_msg = self.loc.get('err_join_no_id', fallback="FATAL: Could not find unique node ID. Join module cannot function.")
            self.logger(error_msg, "ERROR")
            raise ValueError("Join module requires a unique node ID from the executor.")
        if payload is None and mode != 'SIMULATE':
             self.logger(self.loc.get('warn_join_no_payload', node_id=node_instance_id, fallback=f"Join node '{node_instance_id}' executed with no input payload. This should not happen."), "WARN")
        with self.lock:
            if mode == 'SIMULATE':
                status_updater("Simulation: Merging and continuing", "WARN")
                return {"payload": payload, "output_name": "output"}
            state_key = f"join_module_state::{node_instance_id}"
            current_state = self.state_manager.get(state_key, {'received_payloads': []})
            current_state['received_payloads'].append(payload)
            self.logger(self.loc.get('log_join_payload_received', node_id=node_instance_id, count=len(current_state['received_payloads'])), "DEBUG")
            try:
                expected_inputs = int(config.get('expected_inputs', 2))
            except (ValueError, TypeError):
                expected_inputs = 2
                self.logger(self.loc.get('warn_join_invalid_config', node_id=node_instance_id, fallback=f"Configuration 'expected_inputs' for Join node '{node_instance_id}' is invalid. Using default of 2."), "WARN")
            received_count = len(current_state['received_payloads'])
            status_updater(self.loc.get('status_join_waiting', received=received_count, total=expected_inputs), "INFO")
            if received_count >= expected_inputs:
                self.logger(self.loc.get('log_join_complete', count=received_count, node_id=node_instance_id), "SUCCESS")
                final_payload = {'data': {}, 'history': []}
                collected_data = []
                base_history_set = False
                for p_load in current_state['received_payloads']:
                    if isinstance(p_load, dict):
                        collected_data.append(p_load.get('data', {}))
                        if not base_history_set:
                            final_payload['history'] = p_load.get('history', [])
                            base_history_set = True
                final_payload['data']['joined_data'] = collected_data
                self.logger(f"Joined payload: {json.dumps(final_payload, indent=2)}", "DETAIL")
                self.state_manager.delete(state_key)
                return {"payload": final_payload, "output_name": "output"}
            else:
                self.state_manager.set(state_key, current_state)
                return None
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        join_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_join_title', fallback="Join Configuration"))
        join_frame.pack(fill='x', padx=5, pady=(5, 10), expand=True)
        prop_frame = ttk.Frame(join_frame)
        prop_frame.pack(fill='x', padx=10, pady=10)
        ttk.Label(prop_frame, text=self.loc.get('prop_join_expected_inputs', fallback="Number of Expected Inputs:")).pack(side='left')
        created_vars['expected_inputs'] = ttk.IntVar(value=config.get('expected_inputs', 2))
        ttk.Entry(prop_frame, textvariable=created_vars['expected_inputs'], width=5).pack(side='left', padx=5)
        return created_vars
    def get_data_preview(self, config: dict):
        """
        Provides a sample of what this module might output for the Data Canvas.
        """
        expected_inputs = config.get('expected_inputs', 2)
        return {
            "joined_data": [
                {f"data_from_input_{i+1}": "..."} for i in range(expected_inputs)
            ]
        }
