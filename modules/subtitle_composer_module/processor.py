#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\subtitle_composer_module\processor.py
# JUMLAH BARIS : 127
#######################################################################

import ttkbootstrap as ttk
from tkinter import StringVar, Text
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.ui_shell.custom_widgets.scrolled_frame import ScrolledFrame
import json
class SubtitleComposerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    """
    Module to visually compose a list of subtitles with timestamps.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        status_updater("Composing subtitle data...", "INFO")
        subtitle_entries = config.get('subtitle_entries', [])
        if not isinstance(subtitle_entries, list):
            self.logger("Subtitle entries config is not a list, skipping.", "WARN")
            subtitle_entries = []
        output_data = []
        for entry in subtitle_entries:
            try:
                start_time = entry.get('start', '00:00:00.000')
                end_time = entry.get('end', '00:00:00.000')
                text = entry.get('text', '')
                if not (isinstance(start_time, str) and isinstance(end_time, str) and isinstance(text, str)):
                    self.logger(f"Skipping invalid subtitle entry: {entry}", "WARN")
                    continue
                output_data.append({
                    "start": start_time,
                    "end": end_time,
                    "text": text
                })
            except Exception as e:
                self.logger(f"Error processing a subtitle entry: {e}", "WARN")
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['subtitle_data'] = output_data
        self.logger(f"Successfully composed {len(output_data)} subtitle entries.", "SUCCESS")
        status_updater("Subtitle data composed.", "SUCCESS")
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        self.subtitle_rows = []
        main_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_subtitle_entries_label'))
        main_frame.pack(fill='both', expand=True, padx=5, pady=5)
        header = ttk.Frame(main_frame)
        header.pack(fill='x', padx=5, pady=(5,0))
        ttk.Label(header, text=self.loc.get('prop_subtitle_start_label'), width=15).pack(side='left')
        ttk.Label(header, text=self.loc.get('prop_subtitle_end_label'), width=15).pack(side='left', padx=5)
        ttk.Label(header, text=self.loc.get('prop_subtitle_text_label')).pack(side='left', fill='x', expand=True)
        scrolled_frame = ScrolledFrame(main_frame)
        scrolled_frame.pack(fill='both', expand=True, pady=5)
        self.rows_container = scrolled_frame.scrollable_frame
        def _add_row(start_val="", end_val="", text_val=""):
            row_frame = ttk.Frame(self.rows_container)
            row_frame.pack(fill='x', pady=2)
            start_var = StringVar(value=start_val)
            end_var = StringVar(value=end_val)
            text_var = StringVar(value=text_val)
            ttk.Entry(row_frame, textvariable=start_var, width=15).pack(side='left')
            ttk.Entry(row_frame, textvariable=end_var, width=15).pack(side='left', padx=5)
            ttk.Entry(row_frame, textvariable=text_var).pack(side='left', fill='x', expand=True)
            remove_button = ttk.Button(row_frame, text="X", width=2, bootstyle="danger", command=lambda rf=row_frame: _remove_row(rf))
            remove_button.pack(side='left', padx=(5,0))
            self.subtitle_rows.append({
                'frame': row_frame,
                'start': start_var,
                'end': end_var,
                'text': text_var
            })
        def _remove_row(row_frame_to_remove):
            row_to_delete = next((row for row in self.subtitle_rows if row['frame'] == row_frame_to_remove), None)
            if row_to_delete:
                row_frame_to_remove.destroy()
                self.subtitle_rows.remove(row_to_delete)
        add_button = ttk.Button(main_frame, text=self.loc.get('prop_subtitle_add_button'), command=_add_row, bootstyle="success-outline")
        add_button.pack(fill='x', padx=5, pady=5)
        saved_entries = config.get('subtitle_entries', [])
        if saved_entries and isinstance(saved_entries, list): # PENAMBAHAN KODE: Pengecekan keamanan
            for entry in saved_entries:
                if isinstance(entry, dict): # PENAMBAHAN KODE: Pengecekan keamanan
                    _add_row(entry.get('start'), entry.get('end'), entry.get('text'))
        else:
            _add_row("00:00:00.000", "00:00:05.000", "Your first subtitle text.")
        class SubtitleEntriesVar:
            def __init__(self, ui_rows_list):
                self.ui_rows = ui_rows_list
            def get(self):
                entries = []
                for row in self.ui_rows:
                    if row['frame'].winfo_exists():
                        entries.append({
                            'start': row['start'].get(),
                            'end': row['end'].get(),
                            'text': row['text'].get()
                        })
                return entries
        property_vars['subtitle_entries'] = SubtitleEntriesVar(self.subtitle_rows)
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        """
        Provides a sample of the composed subtitle data structure.
        """
        entries = config.get('subtitle_entries', [])
        preview = {
            'status': f"Composing {len(entries)} subtitle entries.",
            'sample_output_format': [
                {
                    "start": "HH:MM:SS.ms",
                    "end": "HH:MM:SS.ms",
                    "text": "Your subtitle text here."
                }
            ]
        }
        return preview
