#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\Users\User\Desktop\FLOWORK\tools\licensing\generator.py
#######################################################################
import json
import base64
from datetime import datetime, timedelta
import os
from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
from dateutil.relativedelta import relativedelta

class LicenseGenerator:
    """Encapsulates all logic for generating RSA keys and creating signed license files."""

    def __init__(self, private_key_file="private_key.pem", public_key_file="public_key.pem"):
        self.private_key_file = private_key_file
        self.public_key_file = public_key_file

    def generate_keys(self):
        """Creates a pair of RSA keys (private and public) if they don't exist."""
        print(f"Mencari kunci di '{self.private_key_file}' dan '{self.public_key_file}'...")
        if os.path.exists(self.private_key_file) and os.path.exists(self.public_key_file):
            print("Kunci sudah ada. Melewati pembuatan kunci baru.")
            return

        print("Membuat pasangan kunci baru...")
        key = RSA.generate(2048)

        private_key = key.export_key()
        with open(self.private_key_file, "wb") as f:
            f.write(private_key)
        print(f" -> Kunci privat berhasil disimpan ke: {self.private_key_file}")

        public_key = key.publickey().export_key()
        with open(self.public_key_file, "wb") as f:
            f.write(public_key)
        print(f" -> Kunci publik berhasil disimpan ke: {self.public_key_file}")

        print("\nPERINGATAN: Jaga file 'private_key.pem' dengan sangat baik! Jangan pernah bagikan atau unggah ke repository publik.")

    def create_license_file(self, email: str, output_file: str, duration_days: int = 0, duration_months: int = 0):
        """Creates a signed license file."""
        print("\nMemulai pembuatan file lisensi...")
        if not os.path.exists(self.private_key_file):
            print(f"ERROR: File kunci privat '{self.private_key_file}' tidak ditemukan. Jalankan dengan --generate-keys terlebih dahulu.")
            return

        now = datetime.now()
        expiry_date = now
        if duration_days > 0:
            expiry_date = now + timedelta(days=duration_days)
        elif duration_months > 0:
            expiry_date = now + relativedelta(months=duration_months)

        license_data = {
            "user_email": email,
            "expiry_date": expiry_date.strftime("%Y-%m-%d"),
            "generated_at": now.strftime("%Y-%m-%d %H:%M:%S")
        }

        license_data_str = json.dumps(license_data, sort_keys=True)
        license_data_bytes = license_data_str.encode('utf-8')
        print(f" -> Data lisensi yang akan disegel: {license_data_str}")

        try:
            with open(self.private_key_file, "rb") as f:
                private_key = RSA.import_key(f.read())

            hasher = SHA256.new(license_data_bytes)
            signer = pkcs1_15.new(private_key)
            signature = signer.sign(hasher)
            print(" -> Segel digital berhasil dibuat.")
        except Exception as e:
            print(f"ERROR: Gagal membuat segel digital: {e}")
            return

        final_license_obj = {
            "license_data": license_data_str,
            "signature_b64": base64.b64encode(signature).decode('utf-8')
        }
        final_license_str = json.dumps(final_license_obj)

        try:
            with open(output_file, "w") as f:
                f.write(final_license_str)
            print(f"\nSUKSES! File lisensi '{output_file}' untuk '{email}' telah berhasil dibuat.")
            print(f"Lisensi ini akan berlaku sampai: {license_data['expiry_date']}")
        except IOError as e:
            print(f"ERROR: Gagal menyimpan file lisensi: {e}")
#######################################################################
# dev : awenk audico
# EMAIL SAHIDINAOLA@GMAIL.COM
# WEBSITE WWW.TEETAH.ART
# File NAME : C:\Users\User\Desktop\FLOWORK\tools\licensing\generator.py
#######################################################################