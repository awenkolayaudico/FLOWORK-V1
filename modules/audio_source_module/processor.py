#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\audio_source_module\processor.py
# JUMLAH BARIS : 210
#######################################################################

import os
import time
import json
import shutil
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
from flowork_kernel.utils.file_helper import sanitize_filename
import ttkbootstrap as ttk
from tkinter import StringVar, scrolledtext, filedialog
class AudioSourceModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    """
    Provides an audio source, either from a local file or by generating it via Text-to-Speech.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        source_mode = config.get('source_mode', 'file_path')
        if 'data' not in payload or not isinstance(payload.get('data'), dict):
            payload['data'] = {}
        audio_path = None
        try:
            if source_mode == 'file_path':
                status_updater("Resolving audio file path...", "INFO")
                path_mode = config.get('file_path_mode', 'manual')
                if path_mode == 'manual':
                    audio_path = config.get('manual_path')
                else: # dynamic
                    path_key = config.get('path_input_key')
                    if not path_key: raise ValueError("Payload key for audio path is not set.")
                    audio_path = get_nested_value(payload, path_key)
                if not audio_path or not os.path.isfile(audio_path):
                    raise FileNotFoundError(f"Audio file not found at path: {audio_path}")
                self.logger(f"Sourced audio file: {audio_path}", "SUCCESS")
                status_updater("Audio file located.", "SUCCESS")
            elif source_mode == 'tts':
                status_updater("Preparing for Text-to-Speech generation...", "INFO")
                text_source = config.get('tts_text_source', 'manual')
                text_to_speak = ""
                if text_source == 'manual':
                    text_to_speak = config.get('manual_text')
                else: # dynamic
                    text_key = config.get('text_input_key')
                    if not text_key: raise ValueError("Payload key for TTS text is not set.")
                    text_to_speak = get_nested_value(payload, text_key)
                if not text_to_speak or not isinstance(text_to_speak, str):
                    raise ValueError("Text for TTS is empty or invalid.")
                ai_provider_id = config.get('ai_provider_id')
                if not ai_provider_id: raise ValueError("AI Provider for TTS is not selected.")
                output_folder = config.get('output_folder_tts')
                if not output_folder:
                     raise ValueError("Output folder for TTS is not set.")
                if not os.path.isdir(output_folder):
                    os.makedirs(output_folder, exist_ok=True)
                    self.logger(f"Created TTS output folder: {output_folder}", "INFO")
                status_updater(f"Sending text to '{ai_provider_id}' for synthesis...", "INFO")
                ai_manager = self.kernel.get_service("ai_provider_manager_service")
                if not ai_manager: raise RuntimeError("AIProviderManagerService not available.")
                response = ai_manager.query_ai_by_task('tts', text_to_speak, endpoint_id=ai_provider_id)
                if response.get('type') != 'audio_file':
                    raise TypeError(f"AI provider did not return an audio file. Response: {response}")
                generated_filename = response.get('data')
                temp_audio_path = generated_filename
                if not os.path.isabs(temp_audio_path):
                    temp_audio_path = os.path.join(self.kernel.data_path, "temp_audio", generated_filename)
                if not os.path.exists(temp_audio_path):
                     raise FileNotFoundError(f"Generated audio file not found at expected path: {temp_audio_path}")
                final_filename = f"tts_{sanitize_filename(text_to_speak[:20])}_{int(time.time())}.wav" # Using .wav as it's more standard for TTS output
                audio_path = os.path.join(output_folder, final_filename)
                shutil.move(temp_audio_path, audio_path)
                self.logger(f"TTS audio generated and saved to: {audio_path}", "SUCCESS")
                status_updater("TTS generation complete.", "SUCCESS")
            else:
                raise ValueError(f"Unknown source mode: {source_mode}")
            payload['data']['audio_path'] = audio_path
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"Audio Source module failed: {e}", "ERROR")
            status_updater(f"Error: {e}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        mode_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_audio_source_mode_label'))
        mode_frame.pack(fill='x', padx=5, pady=5)
        source_mode_var = StringVar(value=config.get('source_mode', 'file_path'))
        property_vars['source_mode'] = source_mode_var
        file_path_frame = ttk.Frame(parent_frame)
        tts_frame = ttk.Frame(parent_frame)
        def _toggle_main_mode():
            if source_mode_var.get() == 'file_path':
                tts_frame.pack_forget()
                file_path_frame.pack(fill='both', expand=True)
            else:
                file_path_frame.pack_forget()
                tts_frame.pack(fill='both', expand=True)
        ttk.Radiobutton(mode_frame, text=self.loc.get('source_mode_file'), variable=source_mode_var, value='file_path', command=_toggle_main_mode).pack(anchor='w', padx=10)
        ttk.Radiobutton(mode_frame, text=self.loc.get('source_mode_tts'), variable=source_mode_var, value='tts', command=_toggle_main_mode).pack(anchor='w', padx=10)
        property_vars.update(self._create_file_path_ui(file_path_frame, config, available_vars))
        property_vars.update(self._create_tts_ui(tts_frame, config, available_vars))
        _toggle_main_mode()
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def _create_file_path_ui(self, parent, config, available_vars):
        vars = {}
        path_source_frame = ttk.LabelFrame(parent, text=self.loc.get('prop_path_source_title'))
        path_source_frame.pack(fill='x', padx=5, pady=5, expand=True)
        path_mode_var = StringVar(value=config.get('file_path_mode', 'manual'))
        vars['file_path_mode'] = path_mode_var
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
        ttk.Label(manual_frame, text=self.loc.get('prop_manual_path_label')).pack(anchor='w')
        entry_frame = ttk.Frame(manual_frame)
        entry_frame.pack(fill='x', expand=True)
        manual_path_var = StringVar(value=config.get('manual_path', ''))
        ttk.Entry(entry_frame, textvariable=manual_path_var).pack(side='left', fill='x', expand=True)
        ttk.Button(entry_frame, text="...", command=lambda: manual_path_var.set(filedialog.askopenfilename() or manual_path_var.get()), width=4).pack(side='left', padx=(5,0))
        vars['manual_path'] = manual_path_var
        path_input_key_var = StringVar(value=config.get('path_input_key', ''))
        LabelledCombobox(dynamic_frame, self.loc.get('prop_path_input_key_label'), path_input_key_var, list(available_vars.keys()))
        vars['path_input_key'] = path_input_key_var
        _toggle_path_mode()
        return vars
    def _create_tts_ui(self, parent, config, available_vars):
        vars = {}
        text_source_frame = ttk.LabelFrame(parent, text=self.loc.get('prop_tts_text_source_label'))
        text_source_frame.pack(fill='x', padx=5, pady=5, expand=True)
        tts_text_source_var = StringVar(value=config.get('tts_text_source', 'manual'))
        vars['tts_text_source'] = tts_text_source_var
        manual_text_frame = ttk.Frame(text_source_frame)
        dynamic_text_frame = ttk.Frame(text_source_frame)
        def _toggle_text_mode():
            if tts_text_source_var.get() == 'manual':
                dynamic_text_frame.pack_forget()
                manual_text_frame.pack(fill='x', padx=5, pady=5)
            else:
                manual_text_frame.pack_forget()
                dynamic_text_frame.pack(fill='x', padx=5, pady=5)
        ttk.Radiobutton(text_source_frame, text=self.loc.get('prop_mode_manual'), variable=tts_text_source_var, value='manual', command=_toggle_text_mode).pack(anchor='w', padx=10)
        ttk.Radiobutton(text_source_frame, text=self.loc.get('prop_mode_dynamic'), variable=tts_text_source_var, value='dynamic', command=_toggle_text_mode).pack(anchor='w', padx=10)
        ttk.Label(manual_text_frame, text=self.loc.get('prop_tts_manual_text_label')).pack(anchor='w')
        manual_text_widget = scrolledtext.ScrolledText(manual_text_frame, height=4)
        manual_text_widget.insert("1.0", config.get('manual_text', ''))
        manual_text_widget.pack(fill='x', expand=True)
        vars['manual_text'] = manual_text_widget
        text_input_key_var = StringVar(value=config.get('text_input_key', ''))
        LabelledCombobox(dynamic_text_frame, self.loc.get('prop_tts_input_key_label'), text_input_key_var, list(available_vars.keys()))
        vars['text_input_key'] = text_input_key_var
        _toggle_text_mode()
        ai_frame = ttk.LabelFrame(parent, text=self.loc.get('prop_tts_ai_provider_label'))
        ai_frame.pack(fill='x', padx=5, pady=5, expand=True)
        ai_manager = self.kernel.get_service("ai_provider_manager_service")
        all_endpoints = ai_manager.get_available_providers() if ai_manager else {}
        ai_provider_id_var = StringVar(value=config.get('ai_provider_id', ''))
        LabelledCombobox(ai_frame, self.loc.get('prop_tts_ai_provider_label'), ai_provider_id_var, list(all_endpoints.values())) # Menggunakan nama display
        display_to_id_map = {name: id for id, name in all_endpoints.items()}
        class ProviderVar:
            def __init__(self, tk_var, name_map):
                self.tk_var = tk_var
                self.name_map = name_map
            def get(self):
                display_name = self.tk_var.get()
                return self.name_map.get(display_name)
        vars['ai_provider_id'] = ProviderVar(ai_provider_id_var, display_to_id_map)
        output_folder_frame = ttk.LabelFrame(parent, text=self.loc.get('prop_tts_output_folder_label'))
        output_folder_frame.pack(fill='x', padx=5, pady=5, expand=True)
        output_folder_var = StringVar(value=config.get('output_folder_tts', ''))
        entry_frame = ttk.Frame(output_folder_frame)
        entry_frame.pack(fill='x', padx=5, pady=5)
        ttk.Entry(entry_frame, textvariable=output_folder_var).pack(side='left', fill='x', expand=True)
        ttk.Button(entry_frame, text="...", command=lambda: output_folder_var.set(filedialog.askdirectory() or output_folder_var.get()), width=4).pack(side='left', padx=(5,0))
        vars['output_folder_tts'] = output_folder_var
        return vars
    def get_data_preview(self, config: dict):
        source_mode = config.get('source_mode', 'file_path')
        if source_mode == 'file_path':
            path = config.get('manual_path', 'Not Set')
            return [{'status': 'Will provide audio from file.', 'path': path}]
        else: # tts
            text = config.get('manual_text', 'Sample text not set.')
            return [{'status': 'Will generate audio from text.', 'text_preview': f"{text[:50]}..."}]
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.audio_path",
                "type": "string",
                "description": "The full path to the final audio file (selected or generated)."
            }
        ]
