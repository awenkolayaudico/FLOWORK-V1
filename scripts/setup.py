#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\FLOWORK\scripts\setup.py
# JUMLAH BARIS : 65
#######################################################################

import os
import sys
import subprocess
import shutil
LIBS_FOLDER = "libs"
VENV_FOLDER = ".venv"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def run_command(command, message):
    """Fungsi untuk menjalankan perintah di command prompt dengan pesan status."""
    print(f"  -> {message}")
    try:
        if command[0] != 'poetry':
             full_command = ['poetry', 'run', sys.executable, '-m'] + command
        else:
             full_command = command
        subprocess.run(full_command, check=True, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding='utf-8')
        print(f"  [SUCCESS] {message} selesai.")
        return True
    except FileNotFoundError:
        print(f"  [ERROR] Perintah '{command[0]}' tidak ditemukan. Pastikan Poetry sudah terinstall dan ada di PATH.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Gagal menjalankan: {' '.join(command)}")
        print(f"  -> Pesan Error: {e.stderr.strip()}")
        return False
def main():
    """Fungsi utama untuk melakukan setup environment."""
    os.chdir(PROJECT_ROOT)
    if os.path.isdir(LIBS_FOLDER):
        print(f"[INFO] Folder '{LIBS_FOLDER}' sudah ada. Melewatkan proses instalasi dependensi.")
        return
    print("\n[SETUP] Folder 'libs' tidak ditemukan. Memulai proses instalasi pertama kali...")
    print("        Proses ini mungkin memakan waktu beberapa menit, tergantung kecepatan internet.")
    if not run_command(['poetry', 'config', 'virtualenvs.in-project', 'true'], "Mengatur Poetry untuk membuat .venv lokal..."):
        return
    if not run_command(['poetry', 'install'], f"Membuat virtual environment ({VENV_FOLDER}) dan menginstall dependensi..."):
        return
    temp_req_file = "temp_requirements.txt"
    if not run_command(['poetry', 'export', '-f', 'requirements.txt', '--output', temp_req_file, '--without-hashes'], "Mengekspor daftar dependensi..."):
        return
    pip_command = ['pip', 'install', '--target', LIBS_FOLDER, '-r', temp_req_file]
    if not run_command(pip_command, f"Menginstall semua paket ke dalam folder '{LIBS_FOLDER}'..."):
        if os.path.exists(temp_req_file):
            os.remove(temp_req_file)
        return
    if os.path.exists(temp_req_file):
        os.remove(temp_req_file)
        print(f"  -> File sementara '{temp_req_file}' dibersihkan.")
    print(f"  -> Membuat arsip '{LIBS_FOLDER}.zip'...")
    try:
        shutil.make_archive(LIBS_FOLDER, 'zip', LIBS_FOLDER)
        print(f"  [SUCCESS] Arsip '{LIBS_FOLDER}.zip' berhasil dibuat.")
    except Exception as e:
        print(f"  [ERROR] Gagal membuat arsip '{LIBS_FOLDER}.zip': {e}")
        return
    print("\n[SUCCESS] Proses setup environment selesai!")
if __name__ == "__main__":
    main()
