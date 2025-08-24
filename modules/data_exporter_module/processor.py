#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\data_exporter_module\processor.py
# JUMLAH BARIS : 221
#######################################################################

import os
import csv
import json
import time
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
import ttkbootstrap as ttk
from tkinter import StringVar, BooleanVar, filedialog
try:
    import openpyxl
    OPENPYXL_AVAILABLE = True
except ImportError:
    OPENPYXL_AVAILABLE = False
class DataExporterModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "basic"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        if not OPENPYXL_AVAILABLE:
            self.logger("Library 'openpyxl' is not installed. XLSX export will not be available.", "WARN")
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        data_source_var = config.get('data_source_variable', 'data.scraped_data')
        output_folder = config.get('output_folder')
        output_filename = config.get('output_filename', 'exported_data')
        file_format = config.get('file_format', 'csv')
        file_mode = config.get('file_mode', 'overwrite')
        data_mapping = config.get('data_mapping', [])
        add_timestamp = config.get('add_timestamp', False)
        add_row_number = config.get('add_row_number', False)
        if not output_folder or not output_filename:
            raise ValueError("Output folder and filename must be specified.")
        source_data = get_nested_value(payload, data_source_var)
        if source_data is None:
            raise ValueError(f"Data source variable '{data_source_var}' not found in payload.")
        if isinstance(source_data, dict) and data_mapping:
            self.logger("Data mapping rules found. Transforming raw data.", "INFO")
            status_updater("Transforming data based on mapping...", "INFO")
            transformed_data = {}
            for rule in data_mapping:
                source_key = rule.get('source')
                target_key = rule.get('target')
                if source_key and target_key:
                    if source_key in source_data:
                        transformed_data[target_key] = source_data[source_key]
            data_to_export = [transformed_data]
        elif isinstance(source_data, list):
            self.logger("Input data is already a list. Assuming it's structured.", "INFO")
            data_to_export = source_data
        else:
             raise TypeError(f"Data at '{data_source_var}' is not a list of dictionaries or a single dictionary that can be mapped.")
        if add_timestamp:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            final_filename = f"{output_filename}_{timestamp}"
        else:
            final_filename = output_filename
        final_path = os.path.join(output_folder, f"{final_filename}.{file_format}")
        if add_row_number:
            state_manager = self.kernel.get_service("state_manager")
            if state_manager:
                counter_key = f"data_exporter_counter::{os.path.join(output_folder, output_filename)}"
                if file_mode == 'overwrite' or not os.path.exists(final_path):
                    start_number = 1
                    state_manager.delete(counter_key)
                    self.logger(f"Row number counter for '{os.path.basename(final_path)}' has been reset to 1.", "INFO")
                else:
                    start_number = state_manager.get(counter_key, 1)
                for i, row in enumerate(data_to_export):
                    row_with_number = {'No.': start_number + i}
                    row_with_number.update(row)
                    data_to_export[i] = row_with_number
                state_manager.set(counter_key, start_number + len(data_to_export))
        status_updater(f"Preparing to {file_mode} {len(data_to_export)} records to {os.path.basename(final_path)}", "INFO")
        os.makedirs(output_folder, exist_ok=True)
        try:
            if file_format == 'csv':
                self._write_csv(final_path, data_to_export, config)
            elif file_format == 'xlsx':
                self._write_xlsx(final_path, data_to_export, config)
            else:
                raise ValueError(f"Unsupported file format for append mode: {file_format}")
            status_updater(f"Successfully wrote file to {final_path}", "SUCCESS")
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['exported_file_path'] = final_path
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"Failed to export data: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def _write_csv(self, path, data, config):
        file_mode = config.get('file_mode', 'overwrite')
        delimiter = config.get('csv_delimiter', ',')
        if delimiter == 'tab': delimiter = '\t'
        include_header = config.get('include_header', True)
        file_exists = os.path.isfile(path)
        open_mode = 'a' if file_mode == 'append' else 'w'
        with open(path, open_mode, newline='', encoding='utf-8') as f:
            if not data: return
            writer = csv.DictWriter(f, fieldnames=data[0].keys(), delimiter=delimiter)
            if (not file_exists or file_mode == 'overwrite') and include_header:
                writer.writeheader()
            writer.writerows(data)
    def _write_xlsx(self, path, data, config):
        if not OPENPYXL_AVAILABLE:
            raise ImportError("The 'openpyxl' library is required for XLSX export. Please install it.")
        file_mode = config.get('file_mode', 'overwrite')
        include_header = config.get('include_header', True)
        if file_mode == 'append' and os.path.exists(path):
            workbook = openpyxl.load_workbook(path)
            sheet = workbook.active
        else:
            workbook = openpyxl.Workbook()
            sheet = workbook.active
            if include_header and data:
                sheet.append(list(data[0].keys()))
        if not data:
            workbook.save(path)
            return
        headers = list(data[0].keys())
        for row_data in data:
            sheet.append([row_data.get(h, '') for h in headers])
        workbook.save(path)
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        self.mapping_rows = []
        source_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_data_source_label'))
        source_frame.pack(fill='x', padx=5, pady=5)
        property_vars['data_source_variable'] = StringVar(value=config.get('data_source_variable', 'data.scraped_data'))
        def _update_mapping_options(*args):
            source_data_path = property_vars['data_source_variable'].get()
            nested_keys = [k.replace(f"{source_data_path}.", '') for k in available_vars if k.startswith(f"{source_data_path}.")]
            for row_data in self.mapping_rows:
                if row_data['frame'].winfo_exists():
                    row_data['source_combo']['values'] = nested_keys
        LabelledCombobox(parent=source_frame, label_text=self.loc.get('prop_data_source_label'), variable=property_vars['data_source_variable'], values=list(available_vars.keys()))
        property_vars['data_source_variable'].trace_add('write', _update_mapping_options)
        mapping_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_data_mapping_label'))
        mapping_frame.pack(fill='x', padx=5, pady=5)
        header_frame = ttk.Frame(mapping_frame)
        header_frame.pack(fill='x', padx=5, pady=(5,0))
        ttk.Label(header_frame, text=self.loc.get('mapping_source_header'), width=25).pack(side='left', padx=(0,5))
        ttk.Label(header_frame, text=self.loc.get('mapping_target_header')).pack(side='left')
        self.mapping_container = ttk.Frame(mapping_frame)
        self.mapping_container.pack(fill='x', expand=True, padx=5)
        def _add_mapping_row(source_val="", target_val=""):
            row = ttk.Frame(self.mapping_container)
            row.pack(fill='x', pady=2)
            source_var = StringVar(value=source_val)
            target_var = StringVar(value=target_val)
            source_combo = ttk.Combobox(row, textvariable=source_var, values=[], width=25)
            source_combo.pack(side='left', padx=(0,5))
            ttk.Entry(row, textvariable=target_var).pack(side='left', fill='x', expand=True)
            ttk.Button(row, text="X", width=2, bootstyle="danger", command=row.destroy).pack(side='left', padx=(5,0))
            self.mapping_rows.append({'source': source_var, 'target': target_var, 'frame': row, 'source_combo': source_combo})
        ttk.Button(mapping_frame, text=self.loc.get('mapping_add_rule_button'), command=_add_mapping_row, bootstyle="outline-info").pack(pady=5, padx=5)
        saved_mapping = config.get('data_mapping', [])
        if saved_mapping:
            for rule in saved_mapping:
                _add_mapping_row(rule.get('source',''), rule.get('target',''))
        else:
            _add_mapping_row()
        class MappingVar:
            def __init__(self, ui_rows_list):
                self.mapping_rows = ui_rows_list
            def get(self):
                mapping_list = []
                for row_data in self.mapping_rows:
                    if row_data['frame'].winfo_exists():
                        source = row_data['source'].get()
                        target = row_data['target'].get()
                        if source and target:
                            mapping_list.append({'source': source, 'target': target})
                return mapping_list
        property_vars['data_mapping'] = MappingVar(self.mapping_rows)
        _update_mapping_options()
        output_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_output_config_label'))
        output_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(output_frame, text=self.loc.get('prop_output_folder_label')).pack(anchor='w', padx=5)
        folder_frame = ttk.Frame(output_frame)
        folder_frame.pack(fill='x', padx=5, pady=(0,5))
        property_vars['output_folder'] = StringVar(value=config.get('output_folder', ''))
        ttk.Entry(folder_frame, textvariable=property_vars['output_folder']).pack(side='left', fill='x', expand=True)
        ttk.Button(folder_frame, text="...", command=lambda: property_vars['output_folder'].set(filedialog.askdirectory() or property_vars['output_folder'].get()), width=4).pack(side='left', padx=(5,0))
        ttk.Label(output_frame, text=self.loc.get('prop_output_filename_label')).pack(anchor='w', padx=5)
        property_vars['output_filename'] = StringVar(value=config.get('output_filename', 'exported_data'))
        ttk.Entry(output_frame, textvariable=property_vars['output_filename']).pack(fill='x', padx=5, pady=(0,5))
        format_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_format_options_label'))
        format_frame.pack(fill='x', padx=5, pady=5)
        property_vars['file_mode'] = StringVar(value=config.get('file_mode', 'overwrite'))
        LabelledCombobox(parent=format_frame, label_text=self.loc.get('prop_file_mode_label'), variable=property_vars['file_mode'], values=['overwrite', 'append'])
        property_vars['file_format'] = StringVar(value=config.get('file_format', 'csv'))
        LabelledCombobox(parent=format_frame, label_text=self.loc.get('prop_file_format_label'), variable=property_vars['file_format'], values=['csv', 'xlsx'])
        property_vars['csv_delimiter'] = StringVar(value=config.get('csv_delimiter', ','))
        LabelledCombobox(parent=format_frame, label_text=self.loc.get('prop_csv_delimiter_label'), variable=property_vars['csv_delimiter'], values=[',', ';', '|', 'tab'])
        property_vars['include_header'] = BooleanVar(value=config.get('include_header', True))
        ttk.Checkbutton(format_frame, text=self.loc.get('prop_include_header_label'), variable=property_vars['include_header']).pack(anchor='w', padx=5, pady=5)
        property_vars['add_row_number'] = BooleanVar(value=config.get('add_row_number', False))
        ttk.Checkbutton(format_frame, text=self.loc.get('prop_add_row_number_label'), variable=property_vars['add_row_number']).pack(anchor='w', padx=5, pady=5)
        property_vars['add_timestamp'] = BooleanVar(value=config.get('add_timestamp', False))
        ttk.Checkbutton(format_frame, text=self.loc.get('prop_add_timestamp_label'), variable=property_vars['add_timestamp']).pack(anchor='w', padx=5, pady=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        filename_parts = [config.get('output_filename', 'export')]
        if config.get('add_timestamp', True):
            filename_parts.append("YYYYMMDD_HHMMSS")
        filename = f"{'_'.join(filename_parts)}.{config.get('file_format', 'csv')}"
        mapping_rules = config.get('data_mapping', [])
        preview_text = f"Will transform data using {len(mapping_rules)} rule(s) and save to {filename}."
        return [{'status': preview_text}]
