#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\data_parser_module\processor.py
# JUMLAH BARIS : 99
#######################################################################

from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer, EnumVarWrapper
from flowork_kernel.ui_shell.shared_properties import create_debug_and_reliability_ui
import ttkbootstrap as ttk
from tkinter import StringVar
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.factories.ParserFactory import ParserFactory
class DataParserModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    A generic module that uses a selected data formatter to parse raw string data.
    NOW REFACTORED to use ParserFactory, decoupling it from FormatterManager.
    """
    TIER = "free"
    def execute(self, payload, config, status_updater, ui_callback, mode='EXECUTE'):
        formatter_id = config.get('formatter_id')
        data_input_key = config.get('data_input_key')
        if not formatter_id:
            error_msg = "No data formatter has been selected in the node properties."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        if not data_input_key:
            error_msg = "The payload key for the data input has not been selected."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        formatter = ParserFactory.create_parser(self.kernel, formatter_id)
        if not formatter:
            error_msg = f"The selected formatter '{formatter_id}' could not be found or loaded."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        from flowork_kernel.utils.payload_helper import get_nested_value
        raw_data = get_nested_value(payload, data_input_key)
        if raw_data is None:
            error_msg = f"Input data key '{data_input_key}' not found in the payload."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        if not isinstance(raw_data, str):
            error_msg = f"Input data for parsing must be a string, but got {type(raw_data).__name__}."
            self.logger(error_msg, "ERROR")
            status_updater(error_msg, "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
        status_updater(f"Parsing using {formatter_id}...", "INFO")
        try:
            parsed_data = formatter.parse(raw_data)
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['parsed_data'] = parsed_data
            status_updater("Parsing successful!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"Data parser module failed: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            return {"payload": payload, "output_name": "on_failure"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        created_vars = {}
        formatter_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_select_formatter_label'))
        formatter_frame.pack(fill='x', padx=5, pady=5)
        formatter_manager = self.kernel.get_service("formatter_manager_service")
        raw_formatters = formatter_manager.get_available_formatters() if formatter_manager else {}
        label_to_value_map = {name: fid for fid, name in raw_formatters.items()}
        value_to_label_map = {v: k for k, v in label_to_value_map.items()}
        formatter_string_var = StringVar()
        formatter_wrapper = EnumVarWrapper(formatter_string_var, label_to_value_map, value_to_label_map)
        formatter_wrapper.set(config.get('formatter_id'))
        created_vars['formatter_id'] = formatter_wrapper
        ttk.Combobox(formatter_frame, textvariable=formatter_string_var, values=sorted(list(label_to_value_map.keys())), state="readonly").pack(fill='x', expand=True, padx=5, pady=5)
        input_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_select_data_key_label'))
        input_frame.pack(fill='x', padx=5, pady=(0, 10))
        data_key_var = StringVar(value=config.get('data_input_key', ''))
        LabelledCombobox(
            parent=input_frame,
            label_text=self.loc.get('prop_select_data_key_label'),
            variable=data_key_var,
            values=list(available_vars.keys())
        )
        created_vars['data_input_key'] = data_key_var
        debug_vars = create_debug_and_reliability_ui(parent_frame, config, self.loc)
        created_vars.update(debug_vars)
        return created_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Data parsing depends on dynamic input from payload.'}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.parsed_data",
                "type": "any",
                "description": "The structured data (e.g., list of dictionaries) after parsing."
            }
        ]
