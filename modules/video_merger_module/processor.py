#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\video_merger_module\processor.py
# JUMLAH BARIS : 282
#######################################################################

import os
import time
import subprocess
import tempfile
import re
import threading
import json
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
try:
    from moviepy.editor import VideoFileClip, concatenate_videoclips
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False
class MoviePyLogger:
    def __init__(self, status_updater_func):
        self.status_updater = status_updater_func
        self.progress_regex = re.compile(r"t: (\d+\.\d+)/(\d+\.\d+)")
    def debug(self, msg):
        pass
    def info(self, msg):
        match = self.progress_regex.search(msg)
        if match:
            current, total = float(match.group(1)), float(match.group(2))
            if total > 0:
                percent = (current / total) * 100
                self.status_updater(f"Rendering... {percent:.1f}%", "INFO")
        else:
             self.status_updater(msg, "INFO")
    def warning(self, msg):
        self.status_updater(msg, "WARN")
    def error(self, msg):
        self.status_updater(msg, "ERROR")
    def __call__(self, **kwargs):
        """
        Makes the logger instance callable to be compatible with moviepy's proglog.
        This handles progress bar updates.
        """
        if 'bar_name' in kwargs and 'index' in kwargs and 'total' in kwargs:
            if kwargs['total'] > 0:
                percent = (kwargs['index'] / kwargs['total']) * 100
                self.info(f"t: {kwargs['index']}/{kwargs['total']} ({percent:.1f}%)")
    def iter_bar(self, **kwargs):
        """
        Handles iterable progress bars from proglog by simply returning the iterable.
        This satisfies the moviepy logger API without needing to implement a full bar.
        """
        return kwargs.get('iterable', [])
class VideoMergerModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    TIER = "free"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.ffmpeg_path = os.path.join(self.kernel.project_root_path, "vendor", "ffmpeg", "bin", "ffmpeg.exe")
        if not MOVIEPY_AVAILABLE:
            self.logger("WARNING: The 'moviepy' library is not installed. Compatible mode will be unavailable.", "WARN")
    def _is_ffmpeg_available(self):
        return os.path.exists(self.ffmpeg_path)
    def _get_video_properties(self, file_path):
        """
        Uses ffprobe to get critical properties of a video file for compatibility checking.
        """
        ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
        if not os.path.exists(ffprobe_path):
            raise FileNotFoundError("ffprobe.exe not found alongside ffmpeg.exe")
        command = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,codec_name,r_frame_rate',
            '-of', 'json',
            file_path
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        if not data.get('streams'):
            return None
        stream = data['streams'][0]
        try:
            num, den = map(int, stream.get('r_frame_rate', '0/1').split('/'))
            frame_rate = num / den if den != 0 else 0
        except (ValueError, ZeroDivisionError):
            frame_rate = 0
        return {
            'codec': stream.get('codec_name'),
            'width': stream.get('width'),
            'height': stream.get('height'),
            'fps': frame_rate
        }
    def _monitor_ffmpeg_progress(self, process, total_duration_seconds, status_updater, ui_callback):
        duration_regex = re.compile(r"Duration: (\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        progress_regex = re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})")
        def to_seconds(h, m, s, ms):
            return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 100
        for line in iter(process.stderr.readline, ''):
            duration_match = duration_regex.search(line)
            if duration_match:
                h, m, s, ms = duration_match.groups()
                total_duration_seconds[0] = to_seconds(h, m, s, ms)
                self.logger(f"Detected total video duration: {total_duration_seconds[0]}s", "DEBUG")
                break
        for line in iter(process.stdout.readline, ''):
            if "out_time_ms" in line:
                try:
                    current_time_us = int(line.strip().split('=')[1])
                    current_seconds = current_time_us / 1_000_000
                    if total_duration_seconds[0] > 0:
                        percent = (current_seconds / total_duration_seconds[0]) * 100
                        ui_callback(status_updater, f"Merging... {min(percent, 100):.1f}%", "INFO")
                        time.sleep(0.05)
                except (ValueError, IndexError):
                    continue
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        merge_method_display = config.get('merge_method', 'Fast (Stream Copy)')
        method_key = 'fast' if '(Stream Copy)' in merge_method_display else 'compatible'
        video_list_var = config.get('video_list_variable')
        if not video_list_var:
            raise ValueError("Input variable for video list/folder is not configured.")
        input_path_or_list = get_nested_value(payload, video_list_var)
        video_files = []
        if isinstance(input_path_or_list, list):
            self.logger("Input is a list of files. Proceeding directly.", "INFO")
            video_files = input_path_or_list
        elif isinstance(input_path_or_list, str) and os.path.isdir(input_path_or_list):
            self.logger(f"Input is a folder path. Scanning for video files in: {input_path_or_list}", "INFO")
            status_updater(f"Scanning folder for videos...", "INFO")
            valid_extensions = ('.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv')
            for filename in sorted(os.listdir(input_path_or_list)):
                if filename.lower().endswith(valid_extensions):
                    video_files.append(os.path.join(input_path_or_list, filename))
        else:
            raise ValueError(f"Payload variable '{video_list_var}' is not a valid list of files or a valid folder path.")
        if not video_files:
            raise ValueError("No video files found to merge from the provided input.")
        if method_key == 'fast':
            return self._execute_ffmpeg(payload, video_files, config, status_updater, ui_callback)
        else:
            return self._execute_moviepy(payload, video_files, config, status_updater, ui_callback)
    def _execute_ffmpeg(self, payload, video_files, config, status_updater, ui_callback):
        if not self._is_ffmpeg_available():
            raise FileNotFoundError(self.loc.get('ffmpeg_not_found_error'))
        status_updater("Verifying video compatibility...", "INFO")
        try:
            base_props = self._get_video_properties(video_files[0])
            for i in range(1, len(video_files)):
                current_props = self._get_video_properties(video_files[i])
                if current_props != base_props:
                    error_msg = (f"Incompatible videos for Fast Merge. '{os.path.basename(video_files[i])}' "
                                 f"differs from '{os.path.basename(video_files[0])}'. "
                                 f"Base: {base_props}, Current: {current_props}. "
                                 "Use 'Compatible (Re-encode)' mode instead.")
                    raise ValueError(error_msg)
            self.logger("All videos are compatible for fast merging.", "SUCCESS")
        except Exception as e:
            self.logger(f"Video compatibility check failed: {e}", "ERROR")
            raise e
        output_folder = config.get('output_folder')
        output_filename = config.get('output_filename', 'merged_video_fast')
        list_file_path = ''
        try:
            total_duration = [0]
            ffprobe_path = self.ffmpeg_path.replace('ffmpeg.exe', 'ffprobe.exe')
            if os.path.exists(ffprobe_path):
                for video_file in video_files:
                    try:
                        cmd = [ffprobe_path, '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_file]
                        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                        total_duration[0] += float(result.stdout)
                    except (subprocess.CalledProcessError, ValueError, Exception) as e:
                        self.logger(f"Could not read duration from {video_file} with ffprobe, skipping. Error: {e}", "WARN")
            if total_duration[0] == 0:
                 raise ValueError("Could not determine total duration of input videos. Are the files valid videos?")
            status_updater(self.loc.get('status_creating_ffmpeg_list'), "INFO")
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                for video_file in video_files:
                    safe_path = video_file.replace('\\', '/')
                    f.write(f"file '{safe_path}'\n")
                list_file_path = f.name
            if not output_filename.lower().endswith('.mp4'):
                output_filename += '.mp4'
            final_output_path = os.path.join(output_folder, output_filename)
            command = [self.ffmpeg_path, '-f', 'concat', '-safe', '0', '-i', list_file_path, '-c', 'copy', '-y', '-v', 'info', '-progress', 'pipe:1', final_output_path]
            status_updater(self.loc.get('status_merging_with_ffmpeg'), "INFO")
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            monitor_thread = threading.Thread(target=self._monitor_ffmpeg_progress, args=(process, total_duration, status_updater, ui_callback), daemon=True)
            monitor_thread.start()
            process.wait()
            monitor_thread.join()
            if process.returncode != 0:
                error_output = process.stderr.read()
                self.logger(f"FFmpeg Error:\n{error_output}", "ERROR")
                raise RuntimeError(f"FFmpeg failed with error: {error_output}")
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['merged_video_path'] = final_output_path
            status_updater("Video merge successful (Fast Mode)!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        finally:
            if list_file_path and os.path.exists(list_file_path):
                os.remove(list_file_path)
    def _execute_moviepy(self, payload, video_files, config, status_updater, ui_callback):
        if not MOVIEPY_AVAILABLE:
            raise RuntimeError("The required 'moviepy' library is not installed for compatible mode.")
        output_folder = config.get('output_folder')
        output_filename = config.get('output_filename', 'merged_video_compatible')
        try:
            clips = []
            total_videos = len(video_files)
            for i, video_file in enumerate(video_files):
                if not os.path.exists(video_file):
                    self.logger(f"Skipping non-existent file: {video_file}", "WARN")
                    continue
                status_updater(f"Loading video {i+1}/{total_videos}...", "INFO")
                clips.append(VideoFileClip(video_file))
            if not clips:
                raise ValueError("No valid video files were found to merge.")
            status_updater(f"Concatenating {len(clips)} video clips...", "INFO")
            final_clip = concatenate_videoclips(clips, method="compose")
            if not output_filename.lower().endswith('.mp4'):
                output_filename += '.mp4'
            final_output_path = os.path.join(output_folder, output_filename)
            status_updater(f"Writing final video to {final_output_path}...", "INFO")
            progress_logger = MoviePyLogger(status_updater)
            final_clip.write_videofile(final_output_path, codec='libx264', audio_codec='aac', logger=progress_logger)
            for clip in clips:
                clip.close()
            if 'data' not in payload or not isinstance(payload['data'], dict):
                payload['data'] = {}
            payload['data']['merged_video_path'] = final_output_path
            status_updater("Video merge successful (Compatible Mode)!", "SUCCESS")
            return {"payload": payload, "output_name": "success"}
        except Exception as e:
            self.logger(f"An error occurred during video merging: {e}", "ERROR")
            payload['error'] = str(e)
            return {"payload": payload, "output_name": "error"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        method_frame = ttk.LabelFrame(parent_frame, text=self.loc.get('prop_merge_method_label'))
        method_frame.pack(fill='x', padx=5, pady=5)
        merge_method_display_values = [self.loc.get('merge_method_fast'), self.loc.get('merge_method_compatible')]
        property_vars['merge_method'] = StringVar(value=config.get('merge_method', merge_method_display_values[0]))
        LabelledCombobox(parent=method_frame, label_text=self.loc.get('prop_merge_method_label'), variable=property_vars['merge_method'], values=merge_method_display_values)
        input_frame = ttk.LabelFrame(parent_frame, text="Input Settings")
        input_frame.pack(fill='x', padx=5, pady=5)
        property_vars['video_list_variable'] = StringVar(value=config.get('video_list_variable', 'data.file_list'))
        LabelledCombobox(parent=input_frame, label_text="Video List Variable / Folder Path:", variable=property_vars['video_list_variable'], values=list(available_vars.keys()))
        output_frame = ttk.LabelFrame(parent_frame, text="Output Settings")
        output_frame.pack(fill='x', padx=5, pady=5)
        ttk.Label(output_frame, text="Output Folder:").pack(anchor='w', padx=5)
        folder_frame = ttk.Frame(output_frame)
        folder_frame.pack(fill='x', padx=5, pady=(0, 5))
        property_vars['output_folder'] = StringVar(value=config.get('output_folder', ''))
        ttk.Entry(folder_frame, textvariable=property_vars['output_folder']).pack(side='left', fill='x', expand=True)
        def _browse_folder():
            path = filedialog.askdirectory(title="Select Output Folder")
            if path:
                property_vars['output_folder'].set(path)
        ttk.Button(folder_frame, text="Browse...", command=_browse_folder).pack(side='left', padx=(5,0))
        ttk.Label(output_frame, text="Output Filename (without extension):").pack(anchor='w', padx=5)
        property_vars['output_filename'] = StringVar(value=config.get('output_filename', 'merged_video'))
        ttk.Entry(output_frame, textvariable=property_vars['output_filename']).pack(fill='x', padx=5, pady=(0, 5))
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        loop_vars = shared_properties.create_loop_settings_ui(parent_frame, config, self.loc, available_vars)
        property_vars.update(loop_vars)
        return property_vars
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Video merging is a heavy process and requires a file list input.'}]
    def get_dynamic_output_schema(self, config):
        return [{"name": "data.merged_video_path", "type": "string", "description": "The full local path to the newly created merged video file."}]
