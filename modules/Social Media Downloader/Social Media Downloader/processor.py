#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\modules\Social Media Downloader\Social Media Downloader\processor.py
# JUMLAH BARIS : 148
#######################################################################

import os
import sys
import subprocess
import json
import shutil
import ttkbootstrap as ttk
from tkinter import StringVar, filedialog
from flowork_kernel.api_contract import BaseModule, IExecutable, IConfigurableUI, IDataPreviewer
from flowork_kernel.ui_shell import shared_properties
from flowork_kernel.utils.payload_helper import get_nested_value
from flowork_kernel.ui_shell.components.LabelledCombobox import LabelledCombobox
class SocialMediaDownloaderModule(BaseModule, IExecutable, IConfigurableUI, IDataPreviewer):
    """
    Downloads videos from a list of URLs using the yt-dlp library.
    [FIXED V5] Executes subprocess with the shell=True flag and captures output robustly.
    """
    TIER = "basic"
    def __init__(self, module_id, services):
        super().__init__(module_id, services)
        self.yt_dlp_path = None
    def _find_yt_dlp_executable(self):
        """Finds the absolute path to the yt-dlp executable."""
        if self.yt_dlp_path and os.path.exists(self.yt_dlp_path):
            return self.yt_dlp_path
        found_path = shutil.which('yt-dlp')
        if found_path:
            self.logger(f"Found yt-dlp executable via shutil.which at: {found_path}", "SUCCESS")
            self.yt_dlp_path = found_path
            return found_path
        venv_scripts_path = os.path.join(sys.prefix, 'Scripts')
        potential_path = os.path.join(venv_scripts_path, 'yt-dlp.exe')
        if os.path.exists(potential_path):
            self.logger(f"Found yt-dlp executable in venv: {potential_path}", "SUCCESS")
            self.yt_dlp_path = potential_path
            return potential_path
        self.logger("yt-dlp executable could not be found anywhere.", "CRITICAL")
        return None
    def execute(self, payload: dict, config: dict, status_updater, ui_callback, mode='EXECUTE'):
        yt_dlp_executable = self._find_yt_dlp_executable()
        if not yt_dlp_executable:
            raise FileNotFoundError("Could not find 'yt-dlp' executable.")
        url_list_variable = config.get('url_list_variable')
        url_key = config.get('url_key_in_object')
        output_folder = config.get('output_folder')
        quality = config.get('video_quality', '720p')
        if not all([url_list_variable, url_key, output_folder]):
            raise ValueError("Configuration is incomplete.")
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder, exist_ok=True)
        url_objects = get_nested_value(payload, url_list_variable)
        if not isinstance(url_objects, list):
            raise TypeError(f"The data at '{url_list_variable}' is not a list.")
        quality_map = {
            "best": "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "1080p": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "720p": "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best",
            "480p": "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best",
            "worst": "worstvideo[ext=mp4]+worstaudio[ext=m4a]/worst[ext=mp4]/worst",
        }
        format_string = quality_map.get(quality, quality_map['720p'])
        downloaded_paths = []
        total_videos = len(url_objects)
        for i, item in enumerate(url_objects):
            if not isinstance(item, dict) or not item.get(url_key):
                self.logger(f"Skipping item {i+1}", "WARN")
                continue
            url = item[url_key]
            status_updater(f"Downloading video {i+1}/{total_videos}...", "INFO")
            try:
                temp_filename = f"flowork_dl_{i+1}.%(ext)s"
                temp_output_template = os.path.join(output_folder, temp_filename)
                command_list = [
                    yt_dlp_executable,
                    '--no-warnings',
                    '--restrict-filenames',
                    '--encoding', 'utf-8', # Menambahkan encoding eksplisit
                    '-f', format_string,
                    '-o', temp_output_template,
                    '--print', 'filename',
                    url
                ]
                result = subprocess.run(' '.join(f'"{arg}"' for arg in command_list), 
                                        shell=True, 
                                        capture_output=True, 
                                        text=True, 
                                        encoding='utf-8', 
                                        check=True)
                temp_path = result.stdout.strip().split('\n')[-1]
                if os.path.exists(temp_path):
                    downloaded_paths.append(temp_path)
                    self.logger(f"Successfully downloaded to temp path: {os.path.basename(temp_path)}", "SUCCESS")
                else:
                    self.logger(f"yt-dlp reported success but file not found at temp path: {temp_path}", "ERROR")
            except subprocess.CalledProcessError as e:
                self.logger(f"Failed to download {url}. yt-dlp error: {e.stderr}", "ERROR")
                continue
            except Exception as e:
                self.logger(f"An unexpected Python error occurred while trying to download {url}: {e}", "CRITICAL")
        if 'data' not in payload or not isinstance(payload['data'], dict):
            payload['data'] = {}
        payload['data']['downloaded_files'] = downloaded_paths
        status_updater(f"Finished. Downloaded {len(downloaded_paths)}/{total_videos} videos.", "SUCCESS")
        return {"payload": payload, "output_name": "success"}
    def create_properties_ui(self, parent_frame, get_current_config, available_vars):
        config = get_current_config()
        property_vars = {}
        input_frame = ttk.LabelFrame(parent_frame, text="Input Configuration")
        input_frame.pack(fill='x', padx=5, pady=5, expand=True)
        property_vars['url_list_variable'] = StringVar(value=config.get('url_list_variable', 'data.json_data'))
        LabelledCombobox(
            parent=input_frame,
            label_text=self.loc.get('prop_url_list_variable_label', fallback="URL List Variable:"),
            variable=property_vars['url_list_variable'],
            values=list(available_vars.keys())
        )
        ttk.Label(input_frame, text=self.loc.get('prop_url_key_in_object_label', fallback="URL Key in Object:")).pack(fill='x', padx=5, pady=(5,0))
        property_vars['url_key_in_object'] = StringVar(value=config.get('url_key_in_object', 'url_video'))
        ttk.Entry(input_frame, textvariable=property_vars['url_key_in_object']).pack(fill='x', padx=5, pady=(0, 5))
        output_frame = ttk.LabelFrame(parent_frame, text="Output Settings")
        output_frame.pack(fill='x', padx=5, pady=5, expand=True)
        ttk.Label(output_frame, text=self.loc.get('prop_output_folder_label', fallback="Output Folder:")).pack(fill='x', padx=5, pady=(5,0))
        path_frame = ttk.Frame(output_frame)
        path_frame.pack(fill='x', padx=5, pady=(0, 5))
        property_vars['output_folder'] = StringVar(value=config.get('output_folder', ''))
        ttk.Entry(path_frame, textvariable=property_vars['output_folder']).pack(side='left', fill='x', expand=True)
        ttk.Button(path_frame, text="...", command=lambda: property_vars['output_folder'].set(filedialog.askdirectory() or property_vars['output_folder'].get()), width=4).pack(side='left', padx=(5,0))
        property_vars['video_quality'] = StringVar(value=config.get('video_quality', '720p'))
        LabelledCombobox(
            parent=output_frame,
            label_text=self.loc.get('prop_video_quality_label', fallback="Video Quality:"),
            variable=property_vars['video_quality'],
            values=['best', '1080p', '720p', '480p', 'worst']
        )
        ttk.Separator(parent_frame).pack(fill='x', pady=15, padx=5)
        debug_vars = shared_properties.create_debug_and_reliability_ui(parent_frame, config, self.loc)
        property_vars.update(debug_vars)
        return property_vars
    def get_dynamic_output_schema(self, config):
        return [{"name": "data.downloaded_files", "type": "list", "description": "A list of local file paths for the successfully downloaded videos."}]
    def get_data_preview(self, config: dict):
        return [{'status': 'preview_not_available', 'reason': 'Video downloading is a network and disk operation not suitable for preview.'}]
