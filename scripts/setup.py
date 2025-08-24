# scripts/setup.py

import os
import sys
import subprocess
import shutil
import hashlib
import json
import stat
import time

# --- Konfigurasi ---
LIBS_FOLDER = "libs"
VENV_FOLDER = ".venv"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOCK_FILE_PATH = os.path.join(PROJECT_ROOT, "poetry.lock")
STATE_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "dependency_state.json")

# =================================================================
# === PERUBAHAN DI SINI: Membuat fungsi hapus yang lebih "cerewet" ===
def verbose_rmtree(path):
    """
    Versi rmtree yang lebih informatif (verbose) dan tangguh.
    Melaporkan setiap file yang dihapus dan mencoba mengatasi file terkunci.
    """
    # Pastikan path absolut untuk keamanan
    path = os.path.abspath(path)
    if not os.path.exists(path):
        print(f"  -> Path '{os.path.basename(path)}' tidak ditemukan, tidak perlu dihapus.")
        return
        
    print(f"  -> Menghapus folder '{os.path.basename(path)}' secara rekursif...")
    
    # Berjalan dari bawah ke atas (bottom-up)
    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            filepath = os.path.join(root, name)
            try:
                os.chmod(filepath, stat.S_IWRITE) # Coba buka kunci
                os.unlink(filepath)
                # Tampilkan log hanya jika filenya banyak, agar tidak spam
                # print(f"    - Menghapus file: {os.path.relpath(filepath, path)}")
            except OSError as e:
                print(f"    [WARN] Gagal menghapus file {filepath}: {e}")

        for name in dirs:
            dirpath = os.path.join(root, name)
            try:
                os.rmdir(dirpath)
                # print(f"    - Menghapus folder kosong: {os.path.relpath(dirpath, path)}")
            except OSError as e:
                print(f"    [WARN] Gagal menghapus folder {dirpath}: {e}")
    
    # Hapus folder root-nya setelah isinya kosong
    try:
        os.rmdir(path)
        print(f"  [SUCCESS] Folder '{os.path.basename(path)}' berhasil dihapus.")
    except OSError as e:
         print(f"  [WARN] Gagal menghapus folder root {path}: {e}")

# =================================================================

def run_command(command, message):
    """Fungsi untuk menjalankan perintah dan menampilkan output-nya secara real-time."""
    print(f"\n> {message}")
    try:
        process = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            shell=True
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(f"  {output.strip()}")
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, command)
        print(f"  [SUCCESS] {message} selesai.")
        return True
    except FileNotFoundError:
        print(f"  [ERROR] Perintah '{command[0]}' tidak ditemukan. Pastikan Poetry sudah terinstall.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Gagal menjalankan: {' '.join(command)}")
        print(f"  -> Proses selesai dengan kode error: {e.returncode}")
        return False

def get_lock_hash():
    if not os.path.exists(LOCK_FILE_PATH): return None
    return hashlib.md5(open(LOCK_FILE_PATH,'rb').read()).hexdigest()

def get_last_install_hash():
    if not os.path.exists(STATE_FILE_PATH): return None
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            return json.load(f).get('lock_hash')
    except (IOError, json.JSONDecodeError):
        return None

def save_current_install_hash(lock_hash):
    os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
    with open(STATE_FILE_PATH, 'w') as f:
        json.dump({'lock_hash': lock_hash}, f)

def main():
    os.chdir(PROJECT_ROOT)
    current_hash = get_lock_hash()
    last_hash = get_last_install_hash()

    if current_hash == last_hash and os.path.isdir(LIBS_FOLDER):
        print("[INFO] Dependensi sudah sinkron. Melewatkan instalasi.")
        return

    print("\n[SETUP] Dependensi tidak sinkron atau belum terinstall. Memulai proses...")
    print("        Proses ini mungkin memakan waktu beberapa menit, tergantung kecepatan internet.")
    
    # =================================================================
    # === PERUBAHAN DI SINI: Gunakan fungsi hapus baru kita ===
    verbose_rmtree(os.path.join(PROJECT_ROOT, LIBS_FOLDER))
    verbose_rmtree(os.path.join(PROJECT_ROOT, VENV_FOLDER))
    # =================================================================
    
    if not run_command(['poetry', 'config', 'virtualenvs.in-project', 'true'], "Mengatur Poetry untuk membuat .venv lokal..."):
        return
    if not run_command(['poetry', 'install'], f"Membuat virtual environment & menginstall dependensi..."):
        return
    
    temp_req_file = "temp_requirements.txt"
    if not run_command(['poetry', 'export', '-f', 'requirements.txt', '--output', temp_req_file, '--without-hashes'], "Mengekspor daftar dependensi..."):
        return

    pip_install_cmd = ['poetry', 'run', 'pip', 'install', '--target', LIBS_FOLDER, '-r', temp_req_file]
    if not run_command(pip_install_cmd, f"Menginstall semua paket ke dalam folder '{LIBS_FOLDER}'..."):
        if os.path.exists(temp_req_file): os.remove(temp_req_file)
        return
        
    if os.path.exists(temp_req_file):
        os.remove(temp_req_file)
        print(f"  -> File sementara '{temp_req_file}' dibersihkan.")

    new_hash = get_lock_hash()
    if new_hash:
        save_current_install_hash(new_hash)
        print("  [SUCCESS] Status dependensi baru berhasil disimpan.")

    print("\n[SUCCESS] Proses setup & sinkronisasi dependensi selesai!")

if __name__ == "__main__":
    main()