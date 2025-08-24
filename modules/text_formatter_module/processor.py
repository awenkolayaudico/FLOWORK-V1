#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\text_formatter_module\processor.py
# JUMLAH BARIS : 77
#######################################################################

from flowork_kernel.api_contract import BaseModule
from flowork_kernel.ui_shell.shared_properties import create_debug_and_reliability_ui
import ttkbootstrap as ttk
from tkinter import StringVar
from flowork_kernel.api_contract import IDataPreviewer
class TextFormatterModule(BaseModule, IDataPreviewer):
    """
    A module to format a given text string into different cases.
    """
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        input_key = config.get('input_text_key')
        format_mode = config.get('formatting_mode')
        if not input_key:
            raise ValueError("Input text key is not configured in properties.")
        input_text = payload.get(input_key)
        if not isinstance(input_text, str):
            raise TypeError(f"Input from key '{input_key}' is not a string.")
        status_updater(f"Formatting text to {format_mode}...", "INFO")
        formatted_text = ""
        if format_mode == 'uppercase':
            formatted_text = input_text.upper()
        elif format_mode == 'lowercase':
            formatted_text = input_text.lower()
        elif format_mode == 'titlecase':
            formatted_text = input_text.title()
        else:
            formatted_text = input_text # Default to no change if mode is unknown
        payload['formatted_text'] = formatted_text
        status_updater("Formatting complete!", "SUCCESS")
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        settings_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('text_formatter_prop_title'))
        settings_frame.pack(fill='x', padx=5, pady=10)
        ttk.Label(settings_frame, text=self.loc.get('prop_input_key_label')).pack(anchor='w', padx=10, pady=(5,0))
        input_key_var = StringVar(value=config.get('input_text_key', ''))
        ttk.Combobox(settings_frame, textvariable=input_key_var, values=list(available_vars.keys()), state="readonly").pack(fill='x', padx=10, pady=(0,10))
        created_vars['input_text_key'] = input_key_var
        ttk.Label(settings_frame, text=self.loc.get('prop_format_mode_label')).pack(anchor='w', padx=10, pady=(5,0))
        self.format_modes = {
            self.loc.get('format_mode_upper'): 'uppercase',
            self.loc.get('format_mode_lower'): 'lowercase',
            self.loc.get('format_mode_title'): 'titlecase'
        }
        current_mode_value = config.get('formatting_mode', 'uppercase')
        current_display_name = next((display for display, value in self.format_modes.items() if value == current_mode_value), self.loc.get('format_mode_upper'))
        self.selected_format_display_var = StringVar(value=current_display_name)
        mode_combo = ttk.Combobox(settings_frame, textvariable=self.selected_format_display_var, values=list(self.format_modes.keys()), state="readonly")
        mode_combo.pack(fill='x', padx=10, pady=(0,10))
        formatting_mode_proxy_var = StringVar()
        created_vars['formatting_mode'] = formatting_mode_proxy_var
        def on_save_proxy():
            selected_display = self.selected_format_display_var.get()
            internal_value = self.format_modes.get(selected_display, 'uppercase')
            formatting_mode_proxy_var.set(internal_value)
        parent_frame.on_save_proxy = on_save_proxy
        debug_vars = create_debug_and_reliability_ui(parent_frame, config, self.loc)
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
