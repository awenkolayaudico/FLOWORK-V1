#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\launcher.py
# JUMLAH BARIS : 83
#######################################################################

import sys
import os
import zipfile
import subprocess
import time
import shutil
PYTHON_ZIP_NAME = "python.zip"
PYTHON_DIR_NAME = "python"
LIBS_ZIP_NAME = "libs.zip"
LIBS_DIR_NAME = "libs"
MAIN_SCRIPT = "main.py"
def show_progress(message):
    """Simple progress display for the console."""
    sys.stdout.write(f"\r> {message}")
    sys.stdout.flush()
def extract_archive(zip_name, target_dir, project_root):
    """Generic function to extract a zip file with progress."""
    zip_path = os.path.join(project_root, zip_name)
    target_path = os.path.join(project_root, target_dir)
    if os.path.exists(target_path):
        print(f"'{target_dir}' directory already exists. Skipping extraction.")
        return True
    if not os.path.exists(zip_path):
        print(f"\n[FATAL ERROR] {zip_name} not found. Cannot run the application.")
        return False
    print(f"Extracting '{zip_name}'... Please wait, this might take a moment.")
    try:
        os.makedirs(target_path, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            total_files = len(zip_ref.infolist())
            for i, file_info in enumerate(zip_ref.infolist()):
                zip_ref.extract(file_info, target_path)
                progress_percentage = (i + 1) / total_files * 100
                show_progress(f"Unpacking '{zip_name}': file {i+1}/{total_files} ({progress_percentage:.1f}%)")
        print(f"\nExtraction of '{zip_name}' complete.")
        return True
    except Exception as e:
        print(f"\n[FATAL ERROR] Failed to extract {zip_name}: {e}")
        shutil.rmtree(target_path, ignore_errors=True)
        return False
def main():
    project_root = os.path.dirname(os.path.abspath(__file__))
    print("--- Flowork Portable Launcher ---")
    if not extract_archive(PYTHON_ZIP_NAME, PYTHON_DIR_NAME, project_root):
        time.sleep(5)
        sys.exit(1)
    if not extract_archive(LIBS_ZIP_NAME, LIBS_DIR_NAME, project_root):
        time.sleep(5)
        sys.exit(1)
    python_dir_path = os.path.join(project_root, PYTHON_DIR_NAME)
    python_exe_path = os.path.join(python_dir_path, "python.exe")
    pythonw_exe_path = os.path.join(python_dir_path, "pythonw.exe")
    final_python_executable = None
    if os.path.exists(python_exe_path):
        final_python_executable = python_exe_path
    elif os.path.exists(pythonw_exe_path):
        final_python_executable = pythonw_exe_path
    else:
        print(f"\n[FATAL ERROR] Could not find 'python.exe' or 'pythonw.exe' in the extracted '{PYTHON_DIR_NAME}' folder.")
        time.sleep(5)
        sys.exit(1)
    main_script_path = os.path.join(project_root, MAIN_SCRIPT)
    if not os.path.exists(main_script_path):
        print(f"\n[FATAL ERROR] Main script '{MAIN_SCRIPT}' not found.")
        time.sleep(5)
        sys.exit(1)
    print(f"\nStarting Flowork with '{os.path.basename(final_python_executable)}'...")
    try:
        subprocess.run([final_python_executable, main_script_path], check=True, cwd=project_root)
    except subprocess.CalledProcessError as e:
        print(f"\n[APP ERROR] The application exited with an error (code: {e.returncode}).")
    except Exception as e:
        print(f"\n[LAUNCHER ERROR] Failed to start the main application: {e}")
        time.sleep(10)
if __name__ == "__main__":
    main()
