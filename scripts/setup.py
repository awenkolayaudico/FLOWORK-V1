# scripts/setup.py
import os
import sys
import subprocess
import shutil
import hashlib
import json

# --- Konfigurasi ---
LIBS_FOLDER = "libs"
VENV_FOLDER = ".venv"
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LOCK_FILE_PATH = os.path.join(PROJECT_ROOT, "poetry.lock")
STATE_FILE_PATH = os.path.join(PROJECT_ROOT, "data", "dependency_state.json")

def run_command(command, message):
    """Fungsi untuk menjalankan perintah di command prompt dengan pesan status."""
    print(f"  -> {message}")
    try:
        # Menjalankan semua perintah via 'poetry run' untuk konsistensi
        full_command = ['poetry'] + command
        subprocess.run(full_command, check=True, cwd=PROJECT_ROOT, capture_output=True, text=True, encoding='utf-8')
        print(f"  [SUCCESS] {message} selesai.")
        return True
    except FileNotFoundError:
        print(f"  [ERROR] Perintah 'poetry' tidak ditemukan. Pastikan Poetry sudah terinstall.")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  [ERROR] Gagal menjalankan: {' '.join(command)}")
        print(f"  -> Pesan Error: {e.stderr.strip()}")
        return False

def get_lock_hash():
    """Menghitung hash dari file poetry.lock."""
    if not os.path.exists(LOCK_FILE_PATH):
        return None
    return hashlib.md5(open(LOCK_FILE_PATH,'rb').read()).hexdigest()

def get_last_install_hash():
    """Membaca hash terakhir yang tersimpan."""
    if not os.path.exists(STATE_FILE_PATH):
        return None
    try:
        with open(STATE_FILE_PATH, 'r') as f:
            return json.load(f).get('lock_hash')
    except (IOError, json.JSONDecodeError):
        return None

def save_current_install_hash(lock_hash):
    """Menyimpan hash saat ini ke file state."""
    os.makedirs(os.path.dirname(STATE_FILE_PATH), exist_ok=True)
    with open(STATE_FILE_PATH, 'w') as f:
        json.dump({'lock_hash': lock_hash}, f)

def main():
    """Fungsi utama untuk melakukan setup dan sinkronisasi environment."""
    os.chdir(PROJECT_ROOT)

    current_hash = get_lock_hash()
    last_hash = get_last_install_hash()

    # Cek jika tidak ada perubahan DAN folder libs sudah ada
    if current_hash == last_hash and os.path.isdir(LIBS_FOLDER):
        print("[INFO] Dependensi sudah sinkron. Melewatkan instalasi.")
        return

    print("\n[SETUP] Dependensi tidak sinkron atau belum terinstall. Memulai proses...")
    print("        Proses ini mungkin memakan waktu beberapa menit.")

    # Hapus folder lama untuk memastikan instalasi bersih
    if os.path.isdir(LIBS_FOLDER):
        print(f"  -> Menghapus folder '{LIBS_FOLDER}' lama...")
        shutil.rmtree(LIBS_FOLDER)
    if os.path.isdir(VENV_FOLDER):
        print(f"  -> Menghapus folder '{VENV_FOLDER}' lama...")
        shutil.rmtree(VENV_FOLDER)

    # Jalankan instalasi dari awal
    if not run_command(['config', 'virtualenvs.in-project', 'true'], "Mengatur Poetry untuk membuat .venv lokal..."):
        return
    if not run_command(['install'], f"Membuat virtual environment & menginstall dependensi..."):
        return

    temp_req_file = "temp_requirements.txt"
    if not run_command(['export', '-f', 'requirements.txt', '--output', temp_req_file, '--without-hashes'], "Mengekspor daftar dependensi..."):
        return

    # Gunakan pip dari venv untuk menginstall semua paket ke folder LIBS
    pip_install_cmd = ['run', 'pip', 'install', '--target', LIBS_FOLDER, '-r', temp_req_file]
    if not run_command(pip_install_cmd, f"Menginstall semua paket ke dalam folder '{LIBS_FOLDER}'..."):
        if os.path.exists(temp_req_file): os.remove(temp_req_file)
        return

    if os.path.exists(temp_req_file):
        os.remove(temp_req_file)
        print(f"  -> File sementara '{temp_req_file}' dibersihkan.")

    # Simpan hash baru setelah instalasi berhasil
    new_hash = get_lock_hash()
    if new_hash:
        save_current_install_hash(new_hash)
        print("  [SUCCESS] Status dependensi baru berhasil disimpan.")

    print("\n[SUCCESS] Proses setup & sinkronisasi dependensi selesai!")

if __name__ == "__main__":
    main()