#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\text_to_speech_module\processor.py
# JUMLAH BARIS : 127
#######################################################################

import os
import time
import numpy as np
from scipy.io.wavfile import write
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
class TextToSpeechModule(BaseModule, IExecutable, IConfigurableUI):
    TIER = "free"
    def __init__(self, module_id: str, services: dict):
        super().__init__(module_id, services)
        self.pipelines = {}
        if not TRANSFORMERS_AVAILABLE:
            self.logger("TextToSpeechModule: 'transformers' or 'scipy' library not found. Module will be disabled.", "ERROR")
    def _initialize_pipeline(self, model_folder, status_updater):
        if model_folder in self.pipelines:
            return self.pipelines[model_folder]
        if not TRANSFORMERS_AVAILABLE:
            raise RuntimeError("The 'transformers' or 'scipy' library is not installed.")
        model_path = os.path.join(self.kernel.project_root_path, "ai_models", "audio", "tts", model_folder)
        status_updater(f"Loading local TTS model '{model_folder}'...", "INFO")
        self.logger(f"TTSModule: Lazily loading local model from: {model_path}", "INFO")
        if not os.path.isdir(model_path):
            raise FileNotFoundError(f"Local model directory not found at: {model_path}")
        try:
            tts_pipeline = pipeline("text-to-speech", model=model_path)
            self.pipelines[model_folder] = tts_pipeline
            self.logger(f"TTSModule: Local model '{model_folder}' loaded successfully.", "SUCCESS")
            return tts_pipeline
        except Exception as e:
            self.logger(f"TTSModule: Failed to load local model: {e}", "ERROR")
            raise RuntimeError(f"Failed to load AI model from '{model_path}': {e}")
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        model_folder = config.get('local_model_folder')
        source_variable = config.get('source_variable', 'data.text_to_speak')
        destination_folder = config.get('destination_folder', '')
        new_filename = config.get('new_filename', '').strip()
        if not model_folder:
            raise ValueError("No local TTS model selected in node properties. Please open the node and select a model.")
        if not destination_folder or not os.path.isdir(destination_folder):
            raise FileNotFoundError(f"Destination folder is not valid or does not exist: {destination_folder}")
        text_input = get_nested_value(payload, source_variable)
        if not text_input or not isinstance(text_input, str):
            raise ValueError(f"Input text not found or not a string at payload path: '{source_variable}'")
        tts_pipeline = self._initialize_pipeline(model_folder, status_updater)
        status_updater(f"Generating audio for: '{text_input[:30]}...'", "INFO")
        try:
            output = tts_pipeline(text_input)
            audio_data = output["audio"][0]
            sampling_rate = output["sampling_rate"]
            audio_data_int16 = (audio_data * 32767).astype(np.int16)
            suggested_filename = f"tts_output_{int(time.time())}.wav"
            if new_filename:
                _root, ext = os.path.splitext(suggested_filename)
                final_filename = f"{new_filename}{ext}"
            else:
                final_filename = suggested_filename
            destination_path = os.path.join(destination_folder, final_filename)
            write(destination_path, rate=sampling_rate, data=audio_data_int16)
            self.logger(f"Audio file saved to: {destination_path}", "SUCCESS")
            if 'data' not in payload:
                payload['data'] = {}
            payload['data']['audio_file_path'] = destination_path
            status_updater("Audio file saved successfully!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"An error occurred during TTS processing: {e}", "ERROR")
            raise RuntimeError(f"TTS processing failed: {e}")
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        input_settings_frame = ttk.LabelFrame(parent_frame, text="Input & Model Settings")
        input_settings_frame.pack(fill='x', padx=5, pady=(10, 5))
        tts_models_path = os.path.join(self.kernel.project_root_path, "ai_models", "audio", "tts")
        available_models = []
        if os.path.isdir(tts_models_path):
            available_models = [d for d in os.listdir(tts_models_path) if os.path.isdir(os.path.join(tts_models_path, d))]
        current_model = config.get('local_model_folder', '')
        if not current_model and available_models:
            current_model = available_models[0]
        property_vars['local_model_folder'] = StringVar(value=current_model)
        LabelledCombobox(parent=input_settings_frame, label_text="Local TTS Model:", variable=property_vars['local_model_folder'], values=sorted(available_models))
        property_vars['source_variable'] = StringVar(value=config.get('source_variable', 'data.text_to_speak'))
        LabelledCombobox(parent=input_settings_frame, label_text="Text Input Variable:", variable=property_vars['source_variable'], values=sorted(list(available_vars.keys())))
        output_settings_frame = ttk.LabelFrame(parent_frame, text="Output File Settings")
        output_settings_frame.pack(fill='x', padx=5, pady=5)
        dest_frame = ttk.Frame(output_settings_frame)
        dest_frame.pack(fill='x', pady=5, padx=5)
        ttk.Label(dest_frame, text="Destination Folder:").pack(anchor='w')
        entry_frame = ttk.Frame(dest_frame)
        entry_frame.pack(fill='x', expand=True, pady=(2,0))
        dest_var = StringVar(value=config.get('destination_folder', ''))
        property_vars['destination_folder'] = dest_var
        dest_entry = ttk.Entry(entry_frame, textvariable=dest_var)
        dest_entry.pack(side='left', fill='x', expand=True)
        def _browse_folder():
            folder_selected = filedialog.askdirectory(title="Select Destination Folder")
            if folder_selected:
                dest_var.set(folder_selected)
        browse_button = ttk.Button(entry_frame, text="Browse...", command=_browse_folder)
        browse_button.pack(side='left', padx=(5,0))
        ttk.Label(output_settings_frame, text="New Filename (Optional, no extension):").pack(anchor='w', padx=5)
        property_vars['new_filename'] = StringVar(value=config.get('new_filename', ''))
        ttk.Entry(output_settings_frame, textvariable=property_vars['new_filename']).pack(fill='x', padx=5, pady=(0, 5))
        return property_vars
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.audio_file_path",
                "type": "string",
                "description": "The full local path to the generated .wav audio file."
            }
        ]
