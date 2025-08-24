#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\Users\User\Desktop\FLOWORK\tools\build_system\builder.py
#######################################################################
import os
import shutil
import sys
from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize
from pathlib import Path

class Builder:
    """Encapsulates the logic for building the Flowork application using Cython."""

    def __init__(self, target_paths):
        self.target_paths = target_paths
        self.files_to_protect = []

    def _find_target_files(self):
        """Finds all specific Python files to be compiled."""
        print("Mencari file target spesifik...")
        for path_str in self.target_paths:
            path = Path(path_str)
            if path.is_dir():
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(".py") and file != "__init__.py":
                            self.files_to_protect.append(os.path.join(root, file))
            elif path.is_file() and path.suffix == '.py':
                self.files_to_protect.append(path_str)

        self.files_to_protect = sorted(list(set(self.files_to_protect)))
        print(f"Ditemukan {len(self.files_to_protect)} file target untuk diamankan.")

    def _cleanup(self, build_dir="build"):
        """Cleans up temporary build files."""
        print("\nMembersihkan file sisa build...")
        if os.path.isdir(build_dir):
            shutil.rmtree(build_dir)
            print(f" -> Folder '{build_dir}' berhasil dihapus.")

        for file_path_str in self.files_to_protect:
            file_path = Path(file_path_str)
            c_file = file_path.with_suffix('.c')
            if c_file.exists():
                try:
                    c_file.unlink()
                    print(f" -> File C '{c_file.name}' berhasil dihapus.")
                except OSError as e:
                    print(f" -> Gagal menghapus file C '{c_file.name}': {e}")

    def run_build(self):
        """The main method to start the Cython compilation process."""
        self._find_target_files()

        success_count = 0
        fail_count = 0

        extensions = [
            Extension(
                name=path.replace(os.path.sep, ".")[:-3],
                sources=[path]
            )
            for path in self.files_to_protect
        ]

        print("\nMemulai proses kompilasi ke kode mesin (Cython)...")
        original_argv = sys.argv
        sys.argv = ['build.py', 'build_ext', '--inplace']

        try:
            setup(
                ext_modules=cythonize(
                    extensions,
                    compiler_directives={'language_level': "3"},
                    quiet=True
                )
            )
            success_count = len(extensions)
            print(f"\n[SUKSES] {success_count} file berhasil ditempa menjadi baja!")
        except Exception as e:
            fail_count = len(extensions)
            print(f"\n[GAGAL TOTAL] Terjadi kesalahan fatal saat kompilasi: {e}")
        finally:
            sys.argv = original_argv
            self._cleanup()

        print("\n--- OPERASI PASUKAN KHUSUS SELESAI ---")
        print(f"Total File Target: {len(self.files_to_protect)}")
        print(f"Berhasil Ditempa: {success_count}")
        print(f"Gagal Ditempa  : {fail_count}")

        if fail_count > 0:
            print("\n[!] OPERASI GAGAL! Cek error di atas.")
        else:
            print("\n[✓] MANTAP! ASET-ASET VITAL TELAH DIAMANKAN DENGAN BAJA LAPIS TUJUH!")
            print("Misi pengamanan selesai, Komandan!")

#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\Users\User\Desktop\FLOWORK\tools\build_system\builder.py
#######################################################################