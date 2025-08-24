#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\sub_workflow_module\processor.py
# JUMLAH BARIS : 103
#######################################################################

import ttkbootstrap as ttk
from tkinter import Listbox, Scrollbar, SINGLE, END, messagebox
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
import json
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.custom_widgets.DualListbox import DualListbox
class SubWorkflowModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Modul yang berfungsi untuk menjalankan alur kerja lain (dari preset)
    sebagai sebuah sub-rutin.
    """
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode: str = 'EXECUTE'):
        """
        Mengeksekusi preset sub-workflow yang dipilih.
        """
        ordered_presets = config.get('execution_order', [])
        node_id = config.get('__internal_node_id', 'sub_workflow_node')
        if not ordered_presets:
            status_updater("No presets configured", "ERROR") # MODIFIED: English Log
            raise ValueError("No presets configured to execute in SubWorkflow.")
        final_payload = payload
        total_presets = len(ordered_presets)
        for i, preset_name in enumerate(ordered_presets):
            status_updater(f"Running preset {i+1}/{total_presets}: {preset_name}", "INFO") # MODIFIED: English Log
            preset_manager = self.kernel.get_service("preset_manager_service")
            if not preset_manager:
                raise RuntimeError("PresetManagerService is not available.")
            workflow_data = preset_manager.get_preset_data(preset_name)
            if not workflow_data:
                status_updater(f"Preset '{preset_name}' not found", "ERROR") # MODIFIED: English Log
                raise FileNotFoundError(f"Selected preset '{preset_name}' was not found.")
            if not workflow_data.get('nodes'):
                status_updater(f"Preset '{preset_name}' is empty", "WARN") # MODIFIED: English Log
                self.logger(f"Warning: Preset '{preset_name}' is empty (no nodes). Skipping.", "WARN") # MODIFIED: English Log
                continue
            nodes = {node['id']: node for node in workflow_data.get('nodes', [])}
            connections = {conn['id']: conn for conn in workflow_data.get('connections', [])}
            try:
                sub_context_id = f"{node_id}_sub_{preset_name}"
                workflow_executor = self.kernel.get_service("workflow_executor_service")
                if not workflow_executor:
                    raise RuntimeError("WorkflowExecutorService is not available.")
                current_payload = workflow_executor.execute_workflow_synchronous(
                    nodes=nodes,
                    connections=connections,
                    initial_payload=final_payload,
                    logger=self.logger,
                    status_updater=lambda n_id, msg, lvl: self.logger(f"[{preset_name}] Node {n_id}: {msg}", lvl.upper()),
                    highlighter=lambda *args: None,
                    ui_callback=ui_callback,
                    workflow_context_id=sub_context_id,
                    mode=mode,
                    job_status_updater=None # Sub-workflows don't update main job status directly
                )
                final_payload = current_payload
                if isinstance(final_payload, Exception):
                    raise final_payload
            except Exception as e:
                self.logger(f"Sub-workflow '{preset_name}' failed with error: {e}", "ERROR") # MODIFIED: English Log
                status_updater(f"Error in '{preset_name}'", "ERROR") # MODIFIED: English Log
                raise e
        status_updater(f"All {total_presets} presets completed", "SUCCESS") # MODIFIED: English Log
        return {"output_name": "success", "payload": final_payload}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        """
        [NEW] Creates the custom UI for selecting and ordering presets to execute.
        """
        config = get_current_config()
        created_vars = {}
        main_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('subworkflow_prop_title'))
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        preset_manager = self.kernel.get_service("preset_manager_service")
        all_presets = preset_manager.get_preset_list() if preset_manager else []
        selected_presets = config.get('execution_order', [])
        dual_listbox = DualListbox(main_frame, self.kernel, available_items=all_presets, selected_items=selected_presets)
        dual_listbox.pack(fill='both', expand=True, padx=5, pady=5)
        class ExecutionOrderVar:
            def __init__(self, listbox_widget):
                self.widget = listbox_widget
            def get(self):
                return self.widget.get_selected_items()
        created_vars['execution_order'] = ExecutionOrderVar(dual_listbox)
        ttk.Separator(parent_frame).pack(fill='x', pady=10, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        loop_vars = shared_properties.create_loop_settings_ui(parent_frame, config, self.loc, available_vars)
        created_vars.update(debug_vars)
        created_vars.update(loop_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        """
        [PENAMBAHAN KODE] Provides a sample of what this module might output for the Data Canvas.
        """
        return [{'status': 'preview_not_available', 'reason': 'Sub-workflow execution is too complex to preview.'}]
