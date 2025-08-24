#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\media_merger_module\processor.py
# JUMLAH BARIS : 244
#######################################################################

import os
import json
import threading
import subprocess
import tempfile
import re
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer, EnumVarWrapper
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
import ttkbootstrap as ttk
from tkinter import StringVar, scrolledtext, filedialog
class MediaMergerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    """
    Waits for video, audio, and subtitle data streams and merges them into a single video file.
    """
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.lock = threading.Lock()
        ffmpeg_executable = "ffmpeg.exe" if os.name == 'nt' else "ffmpeg"
        self.ffmpeg_path = os.path.join(self.kernel.project_root_path, "vendor", "ffmpeg", "bin", ffmpeg_executable)
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        node_instance_id = config.get('__internal_node_id')
        if not node_instance_id:
            raise ValueError("FATAL: Could not get unique node ID for state management.")
        state_key = f"media_merger_state::{node_instance_id}"
        with self.lock:
            current_state = self.state_manager.get(state_key, {'video': None, 'audio': None, 'subtitle': None})
            video_var = config.get('video_source_variable')
            audio_var = config.get('audio_source_variable')
            subtitle_var = config.get('subtitle_source_variable')
            if video_var:
                video_path = get_nested_value(payload, video_var)
                if video_path and os.path.isfile(video_path):
                    current_state['video'] = video_path
                    self.logger(f"Received video input: {os.path.basename(video_path)}", "INFO")
            if audio_var:
                audio_path = get_nested_value(payload, audio_var)
                if audio_path and os.path.isfile(audio_path):
                    current_state['audio'] = audio_path
                    self.logger(f"Received audio input: {os.path.basename(audio_path)}", "INFO")
            subtitle_mode = config.get('subtitle_source_mode', 'dynamic')
            if subtitle_mode == 'dynamic':
                if subtitle_var:
                    subtitle_data = get_nested_value(payload, subtitle_var)
                    if subtitle_data:
                        current_state['subtitle'] = subtitle_data
                        self.logger(f"Received dynamic subtitle data.", "INFO")
            else: # manual
                manual_data_str = config.get('subtitle_manual_input', '[]')
                try:
                    manual_data = json.loads(manual_data_str)
                    if manual_data:
                        current_state['subtitle'] = manual_data
                        self.logger(f"Using manually entered subtitle data.", "INFO")
                except json.JSONDecodeError:
                    self.logger("Manual subtitle data is not valid JSON. Ignoring.", "WARN")
            if current_state.get('video') and current_state.get('audio'):
                self.logger("All required inputs received. Starting merge process.", "SUCCESS")
                status_updater("All inputs received. Merging...", "INFO")
                self.state_manager.delete(state_key)
                try:
                    final_video_path = self._run_ffmpeg_merge(current_state, config)
                    payload['data']['final_video_path'] = final_video_path
                    status_updater("Merge complete!", "SUCCESS")
                    return {"payload": payload, "output_name": "success"}
                except Exception as e:
                    self.logger(f"FFmpeg merge process failed: {e}", "ERROR")
                    status_updater(f"Error during merge: {e}", "ERROR")
                    payload['error'] = str(e)
                    return {"payload": payload, "output_name": "error"}
            else:
                waiting_for = []
                if not current_state.get('video'): waiting_for.append('video')
                if not current_state.get('audio'): waiting_for.append('audio')
                status_updater(f"Waiting for: {', '.join(waiting_for)}", "INFO")
                self.state_manager.set(state_key, current_state)
                return None
        return payload
    def _sanitize_path_for_ffmpeg_filter(self, path):
        """Sanitizes a path specifically for use within an FFmpeg -vf filter string on Windows."""
        if not path:
            return ''
        sanitized_path = path.replace('\\', '/')
        sanitized_path = re.sub(r'([A-Za-z]):', r'\1\\:', sanitized_path)
        return sanitized_path
    def _run_ffmpeg_merge(self, state, config):
        video_in = state.get('video')
        audio_in = state.get('audio')
        subtitle_data = state.get('subtitle')
        output_folder = config.get('output_folder')
        output_filename = config.get('output_filename', 'merged_media')
        if not output_folder or not os.path.isdir(output_folder):
            raise ValueError("Output folder is not set or does not exist.")
        final_path = os.path.join(output_folder, f"{output_filename}.mp4")
        video_in_safe = video_in.replace('\\', '/')
        audio_in_safe = audio_in.replace('\\', '/')
        final_path_safe = final_path.replace('\\', '/')
        command = [self.ffmpeg_path, '-y', '-i', video_in_safe, '-i', audio_in_safe]
        subtitle_file_path = None
        complex_filter = ""
        merge_mode = config.get('merge_mode', 'fast')
        video_codec = "libx264" if merge_mode != 'fast' else "copy"
        if subtitle_data:
            subtitle_file_path = self._create_srt_file(subtitle_data)
            subtitle_mode = config.get('subtitle_mode', 'hardsub')
            if subtitle_mode == 'hardsub':
                escaped_subtitle_path = self._sanitize_path_for_ffmpeg_filter(subtitle_file_path)
                complex_filter = f"subtitles={escaped_subtitle_path}"
                if video_codec == "copy":
                    video_codec = "libx264"
                    self.logger("Hardsub mode is active, forcing video re-encoding (ignoring 'Fast' setting).", "WARN")
            else: # softsub
                subtitle_path_safe = subtitle_file_path.replace('\\', '/')
                command.extend(['-i', subtitle_path_safe, '-c:s', 'mov_text'])
        command.extend(['-c:v', video_codec, '-c:a', 'aac'])
        duration_mode = config.get('duration_mismatch_mode', 'shortest')
        if duration_mode == 'shortest':
            command.append('-shortest')
        if complex_filter:
            command.extend(['-vf', complex_filter])
        command.append(final_path_safe)
        self.logger(f"Executing FFmpeg command: {' '.join(command)}", "DEBUG")
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo)
            self.logger(f"FFmpeg output:\n{process.stderr}", "DETAIL")
        except subprocess.CalledProcessError as e:
            self.logger(f"FFmpeg failed with exit code {e.returncode}. Stderr:\n{e.stderr}", "ERROR")
            raise RuntimeError(f"FFmpeg failed: {e.stderr}")
        finally:
            if subtitle_file_path and os.path.exists(subtitle_file_path):
                os.remove(subtitle_file_path)
        return final_path
    def _create_srt_file(self, subtitle_data):
        if not isinstance(subtitle_data, list):
            self.logger("Subtitle data is not a list, cannot create .srt file.", "WARN")
            return None
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.srt', encoding='utf-8') as f:
            srt_path = f.name
            for i, item in enumerate(subtitle_data):
                start = item.get('start', '00:00:00,000').replace('.', ',')
                end = item.get('end', '00:00:00,000').replace('.', ',')
                text = item.get('text', '')
                f.write(f"{i+1}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")
        self.logger(f"Created temporary subtitle file at: {srt_path}", "DEBUG")
        return srt_path
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        input_frame = ttk.LabelFrame(parent_frame, text="Input Sources")
        input_frame.pack(fill='x', padx=5, pady=5, expand=True)
        property_vars['video_source_variable'] = StringVar(value=config.get('video_source_variable', ''))
        LabelledCombobox(input_frame, self.loc.get('prop_video_source_label'), property_vars['video_source_variable'], list(available_vars.keys()))
        property_vars['audio_source_variable'] = StringVar(value=config.get('audio_source_variable', ''))
        LabelledCombobox(input_frame, self.loc.get('prop_audio_source_label'), property_vars['audio_source_variable'], list(available_vars.keys()))
        subtitle_frame = ttk.LabelFrame(parent_frame, text="Subtitle Source")
        subtitle_frame.pack(fill='x', padx=5, pady=5, expand=True)
        subtitle_mode_var = StringVar(value=config.get('subtitle_source_mode', 'dynamic'))
        property_vars['subtitle_source_mode'] = subtitle_mode_var
        dynamic_sub_frame = ttk.Frame(subtitle_frame)
        manual_sub_frame = ttk.Frame(subtitle_frame)
        def _toggle_subtitle_mode():
            if subtitle_mode_var.get() == 'dynamic':
                manual_sub_frame.pack_forget()
                dynamic_sub_frame.pack(fill='x', expand=True, padx=5, pady=5)
            else:
                dynamic_sub_frame.pack_forget()
                manual_sub_frame.pack(fill='both', expand=True, padx=5, pady=5)
        ttk.Radiobutton(subtitle_frame, text=self.loc.get('prop_mode_dynamic'), variable=subtitle_mode_var, value='dynamic', command=_toggle_subtitle_mode).pack(anchor='w', padx=10)
        ttk.Radiobutton(subtitle_frame, text=self.loc.get('prop_mode_manual'), variable=subtitle_mode_var, value='manual', command=_toggle_subtitle_mode).pack(anchor='w', padx=10)
        property_vars['subtitle_source_variable'] = StringVar(value=config.get('subtitle_source_variable', ''))
        LabelledCombobox(dynamic_sub_frame, self.loc.get('prop_subtitle_variable_label'), property_vars['subtitle_source_variable'], list(available_vars.keys()))
        ttk.Label(manual_sub_frame, text=self.loc.get('prop_subtitle_manual_label')).pack(anchor='w')
        manual_text = scrolledtext.ScrolledText(manual_sub_frame, height=6)
        manual_text.insert("1.0", config.get('subtitle_manual_input', ''))
        manual_text.pack(fill='both', expand=True)
        property_vars['subtitle_manual_input'] = manual_text
        _toggle_subtitle_mode()
        output_frame = ttk.LabelFrame(parent_frame, text="Output Settings")
        output_frame.pack(fill='x', padx=5, pady=5, expand=True)
        folder_frame = ttk.Frame(output_frame)
        folder_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(folder_frame, text=self.loc.get('prop_output_folder_label')).pack(anchor='w')
        entry_frame = ttk.Frame(folder_frame)
        entry_frame.pack(fill='x', expand=True, pady=(2,0))
        folder_var = StringVar(value=config.get('output_folder', ''))
        property_vars['output_folder'] = folder_var
        ttk.Entry(entry_frame, textvariable=folder_var).pack(side='left', fill='x', expand=True)
        ttk.Button(entry_frame, text="...", command=lambda: folder_var.set(filedialog.askdirectory() or folder_var.get()), width=4).pack(side='left', padx=(5,0))
        filename_frame = ttk.Frame(output_frame)
        filename_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(filename_frame, text=self.loc.get('prop_output_filename_label')).pack(anchor='w')
        filename_var = StringVar(value=config.get('output_filename', 'merged_media'))
        property_vars['output_filename'] = filename_var
        ttk.Entry(filename_frame, textvariable=filename_var).pack(fill='x')
        advanced_frame = ttk.LabelFrame(parent_frame, text="Advanced Settings")
        advanced_frame.pack(fill='x', padx=5, pady=5, expand=True)
        merge_map = { self.loc.get('merge_mode_fast'): 'fast', self.loc.get('merge_mode_compatible'): 'compatible' }
        merge_var_str = StringVar()
        property_vars['merge_mode'] = EnumVarWrapper(merge_var_str, merge_map, {v: k for k, v in merge_map.items()})
        property_vars['merge_mode'].set(config.get('merge_mode', 'fast'))
        LabelledCombobox(advanced_frame, self.loc.get('prop_merge_mode_label'), merge_var_str, list(merge_map.keys()))
        duration_map = { self.loc.get('duration_mode_shortest'): 'shortest', self.loc.get('duration_mode_longest'): 'longest', self.loc.get('duration_mode_error'): 'error' }
        duration_var_str = StringVar()
        property_vars['duration_mismatch_mode'] = EnumVarWrapper(duration_var_str, duration_map, {v: k for k, v in duration_map.items()})
        property_vars['duration_mismatch_mode'].set(config.get('duration_mismatch_mode', 'shortest'))
        LabelledCombobox(advanced_frame, self.loc.get('prop_duration_mismatch_label'), duration_var_str, list(duration_map.keys()))
        sub_embed_map = { self.loc.get('subtitle_mode_hardsub'): 'hardsub', self.loc.get('subtitle_mode_softsub'): 'softsub' }
        sub_embed_var_str = StringVar()
        property_vars['subtitle_mode'] = EnumVarWrapper(sub_embed_var_str, sub_embed_map, {v: k for k, v in sub_embed_map.items()})
        property_vars['subtitle_mode'].set(config.get('subtitle_mode', 'hardsub'))
        LabelledCombobox(advanced_frame, self.loc.get('prop_subtitle_embed_mode_label'), sub_embed_var_str, list(sub_embed_map.keys()))
        return property_vars
    def get_data_preview(self, config: dict):
        return {
            'module_function': 'Merge Video, Audio, and Subtitles',
            'video_source': config.get('video_source_variable', 'Not Set'),
            'audio_source': config.get('audio_source_variable', 'Not Set'),
            'subtitle_source': f"{config.get('subtitle_source_mode', 'dynamic')} mode",
            'merge_method': config.get('merge_mode', 'fast'),
            'duration_handling': config.get('duration_mismatch_mode', 'shortest')
        }
    def get_dynamic_output_schema(self, config):
        return [
            {
                "name": "data.final_video_path",
                "type": "string",
                "description": "The full path of the final merged video file."
            }
        ]
