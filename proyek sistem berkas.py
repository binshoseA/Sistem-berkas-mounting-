from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil

# Konfigurasi direktori dan berkas
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data_latihan"
BACKUP_DIR = BASE_DIR / "backup"
LOG_FILE = BASE_DIR / "aktivitas.log"
STATE_FILE = BACKUP_DIR / ".last_backup_hashes.json"

KATEGORI_FOLDER = ["PUBLIC", "DATA_ANGGOTA", "DATA_RAHASIA"]

# Matriks hak akses: R = Read (lihat/baca), W = Write (buat/ubah/hapus)
MATRIKS_IZIN = {
    "owner": {
        "PUBLIC": {"R", "W"},
        "DATA_ANGGOTA": {"R", "W"},
        "DATA_RAHASIA": {"R", "W"},
    },
    "anggota": {
        "PUBLIC": {"R"},
        "DATA_ANGGOTA": {"R", "W"},
        "DATA_RAHASIA": set(),
    },
    "tamu": {
        "PUBLIC": {"R"},
        "DATA_ANGGOTA": set(),
        "DATA_RAHASIA": set(),
    },
}

# Status awal aplikasi
is_mounted = False
peran_aktif = "tamu"


def inisialisasi_lingkungan():
  """Membuat folder latihan, folder backup, dan file contoh jika belum ada."""
  BACKUP_DIR.mkdir(exist_ok=True)
  for kategori in KATEGORI_FOLDER:
    (DATA_DIR / kategori).mkdir(parents=True, exist_ok=True)

  file_awal = {
      DATA_DIR
      / "PUBLIC"
      / "pengumuman.txt": (
          "Rapat umum organisasi dilaksanakan hari Jumat pukul 15.00 WIB.\n"
      ),
      DATA_DIR
      / "DATA_ANGGOTA"
      / "tugas.txt": (
          "Daftar piket dan pembagian tugas kepanitiaan semester ini.\n"
      ),
      DATA_DIR
      / "DATA_RAHASIA"
      / "anggaran.txt": (
          "Saldo kas organisasi: Rp 5.000.000 (Dokumen Rahasia Pengurus).\n"
      ),
  }

  for path_file, isi in file_awal.items():
    if not path_file.exists():
      path_file.write_text(isi, encoding="utf-8")


def catat_log(operasi: str, target: str, status: str):
  """Mencatat waktu, peran, operasi, target, dan status ke aktivitas.log."""
  waktu = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  baris = f"{waktu} | {peran_aktif} | {operasi} | {target} | {status}\n"
  with LOG_FILE.open("a", encoding="utf-8") as f:
    f.write(baris)


def cek_mount(operasi: str, target: str = "-") -> bool:
  """Memastikan penyimpanan sudah di-mount sebelum akses file."""
  if not is_mounted:
    print(
        "\n[DITOLAK] Akses ditolak karena storage belum di-mount (status:"
        " UNMOUNTED)."
    )
    print("          Silakan pilih menu [1] untuk melakukan mount terlebih dahulu.")
    catat_log(operasi, target, "DITOLAK (BELUM_MOUNT)")
    return False
  return True


def cek_izin(kategori: str, hak: str, operasi: str, target: str) -> bool:
  """Memvalidasi izin R atau W berdasarkan peran aktif dan folder kategori."""
  izin_peran = MATRIKS_IZIN.get(peran_aktif, {}).get(kategori, set())
  if hak not in izin_peran:
    label_hak = "baca (R)" if hak == "R" else "tulis/hapus (W)"
    print(
        f"\n[DITOLAK] Akses ditolak! Peran '{peran_aktif}' tidak memiliki izin"
        f" {label_hak} pada folder {kategori}."
    )
    catat_log(operasi, target, "DITOLAK (IZIN_AKSES)")
    return False
  return True


def pilih_kategori() -> str | None:
  """Menampilkan pilihan folder kategori dan mengembalikan nama folder."""
  print("\nPilih Kategori Folder:")
  for idx, nama in enumerate(KATEGORI_FOLDER, start=1):
    print(f"  {idx}. {nama}")
  pilihan = input("Masukkan nomor atau nama folder: ").strip().upper()

  if pilihan in {"1", "PUBLIC"}:
    return "PUBLIC"
  if pilihan in {"2", "DATA_ANGGOTA"}:
    return "DATA_ANGGOTA"
  if pilihan in {"3", "DATA_RAHASIA"}:
    return "DATA_RAHASIA"

  print("[GAGAL] Kategori folder tidak valid.")
  return None


def validasi_nama_file(nama_file: str) -> bool:
  """Memastikan nama file sederhana, berakhiran .txt, tanpa spasi atau garis miring."""
  if not nama_file.endswith(".txt") or nama_file == ".txt":
    return False
  if " " in nama_file or "/" in nama_file or "\\" in nama_file:
    return False
  return True


def toggle_mount():
  """Mengubah status mounted <-> unmounted."""
  global is_mounted
  is_mounted = not is_mounted
  status_teks = "MOUNTED" if is_mounted else "UNMOUNTED"
  operasi = "MOUNT" if is_mounted else "UNMOUNT"
  print(f"\n[BERHASIL] Status penyimpanan sekarang: {status_teks}")
  catat_log(operasi, "data_latihan", "BERHASIL")


def ganti_peran():
  """Mengganti peran pengguna aktif."""
  global peran_aktif
  print("\nPilih Peran Pengguna:")
  print("  1. owner")
  print("  2. anggota")
  print("  3. tamu")
  pilihan = input("Masukkan nomor atau nama peran: ").strip().lower()

  mapping = {
      "1": "owner",
      "owner": "owner",
      "2": "anggota",
      "anggota": "anggota",
      "3": "tamu",
      "tamu": "tamu",
  }
  if pilihan in mapping:
    peran_aktif = mapping[pilihan]
    print(f"\n[BERHASIL] Peran aktif diubah menjadi: {peran_aktif}")
    catat_log("GANTI_PERAN", peran_aktif, "BERHASIL")
  else:
    print("\n[GAGAL] Peran tidak dikenali.")


def lihat_daftar_file():
  """Menampilkan daftar file .txt pada folder kategori."""
  if not cek_mount("LIST_FILE"):
    return

  kategori = pilih_kategori()
  if not kategori:
    return

  if not cek_izin(kategori, "R", "LIST_FILE", kategori):
    return

  folder_target = DATA_DIR / kategori
  daftar = sorted(folder_target.glob("*.txt"))
  print(f"\n--- Daftar File di {kategori} ---")
  if not daftar:
    print("(Belum ada file .txt)")
  else:
    for f in daftar:
      print(f"- {f.name} ({f.stat().st_size} byte)")
  catat_log("LIST_FILE", kategori, "BERHASIL")


def baca_file():
  """Membaca isi file .txt dari folder kategori."""
  if not cek_mount("READ_FILE"):
    return

  kategori = pilih_kategori()
  if not kategori:
    return

  nama_file = input("Masukkan nama file (contoh: pengumuman.txt): ").strip()
  target_rel = f"{kategori}/{nama_file}"

  if not cek_izin(kategori, "R", "READ_FILE", target_rel):
    return

  path_file = DATA_DIR / kategori / nama_file
  if not path_file.is_file():
    print(f"\n[GAGAL] File '{target_rel}' tidak ditemukan.")
    catat_log("READ_FILE", target_rel, "GAGAL (TIDAK_DITEMUKAN)")
    return

  isi = path_file.read_text(encoding="utf-8")
  print(f"\n=== ISI FILE: {target_rel} ===")
  print(isi.rstrip())
  print("=" * (18 + len(target_rel)))
  catat_log("READ_FILE", target_rel, "BERHASIL")


def buat_file():
  """Membuat file .txt baru pada folder kategori."""
  if not cek_mount("CREATE_FILE"):
    return

  kategori = pilih_kategori()
  if not kategori:
    return

  nama_file = input("Masukkan nama file baru (akhiran .txt): ").strip()
  target_rel = f"{kategori}/{nama_file}"

  if not cek_izin(kategori, "W", "CREATE_FILE", target_rel):
    return

  if not validasi_nama_file(nama_file):
    print(
        "\n[DITOLAK] Nama file tidak valid! Gunakan nama sederhana berakhiran"
        " .txt tanpa spasi atau garis miring."
    )
    catat_log("CREATE_FILE", target_rel, "DITOLAK (NAMA_INVALID)")
    return

  path_file = DATA_DIR / kategori / nama_file
  if path_file.exists():
    print(
        f"\n[GAGAL] File '{target_rel}' sudah ada. Gunakan menu Edit/Perbarui"
        " File."
    )
    catat_log("CREATE_FILE", target_rel, "GAGAL (SUDAH_ADA)")
    return

  isi = input("Masukkan isi teks file: ")
  path_file.write_text(isi + "\n", encoding="utf-8")
  print(f"\n[BERHASIL] File '{target_rel}' berhasil dibuat dan disimpan.")
  catat_log("CREATE_FILE", target_rel, "BERHASIL")


def edit_file():
  """Memperbarui isi file .txt yang sudah ada (atau membuat jika diizinkan)."""
  if not cek_mount("UPDATE_FILE"):
    return

  kategori = pilih_kategori()
  if not kategori:
    return

  nama_file = input("Masukkan nama file yang akan diperbarui (.txt): ").strip()
  target_rel = f"{kategori}/{nama_file}"

  if not cek_izin(kategori, "W", "UPDATE_FILE", target_rel):
    return

  if not validasi_nama_file(nama_file):
    print(
        "\n[DITOLAK] Nama file tidak valid! Gunakan nama sederhana berakhiran"
        " .txt tanpa spasi atau garis miring."
    )
    catat_log("UPDATE_FILE", target_rel, "DITOLAK (NAMA_INVALID)")
    return

  path_file = DATA_DIR / kategori / nama_file
  if path_file.exists():
    print(f"Isi saat ini: {path_file.read_text(encoding='utf-8').strip()}")
    mode = (
        input(
            "Pilih mode edit — [1] Timpa seluruh isi | [2] Tambah baris baru: "
        )
        .strip()
    )
    isi_baru = input("Masukkan teks baru: ")
    if mode == "2":
      with path_file.open("a", encoding="utf-8") as f:
        f.write(isi_baru + "\n")
    else:
      path_file.write_text(isi_baru + "\n", encoding="utf-8")
    print(f"\n[BERHASIL] File '{target_rel}' berhasil diperbarui.")
  else:
    isi_baru = input("File belum ada. Masukkan isi untuk membuat file baru: ")
    path_file.write_text(isi_baru + "\n", encoding="utf-8")
    print(f"\n[BERHASIL] File baru '{target_rel}' berhasil disimpan.")

  catat_log("UPDATE_FILE", target_rel, "BERHASIL")


def hapus_file():
  """Fitur mandiri wajib: Menghapus file jika diizinkan dan dengan konfirmasi."""
  if not cek_mount("DELETE_FILE"):
    return

  kategori = pilih_kategori()
  if not kategori:
    return

  nama_file = input("Masukkan nama file yang akan dihapus (.txt): ").strip()
  target_rel = f"{kategori}/{nama_file}"

  if not cek_izin(kategori, "W", "DELETE_FILE", target_rel):
    return

  path_file = DATA_DIR / kategori / nama_file
  if not path_file.is_file():
    print(f"\n[GAGAL] File '{target_rel}' tidak ditemukan.")
    catat_log("DELETE_FILE", target_rel, "GAGAL (TIDAK_DITEMUKAN)")
    return

  konfirmasi = (
      input(f"Yakin ingin menghapus '{target_rel}' secara permanen? (y/n): ")
      .strip()
      .lower()
  )
  if konfirmasi == "y":
    path_file.unlink()
    print(f"\n[BERHASIL] File '{target_rel}' telah dihapus.")
    catat_log("DELETE_FILE", target_rel, "BERHASIL")
  else:
    print("\n[DIBATALKAN] Penghapusan file dibatalkan oleh pengguna.")
    catat_log("DELETE_FILE", target_rel, "DIBATALKAN")


def hitung_hash_semua_file() -> dict[str, str]:
  """Menghitung hash SHA-256 seluruh file di data_latihan untuk pelacakan backup."""
  hasil = {}
  for path_file in sorted(DATA_DIR.rglob("*.txt")):
    rel = path_file.relative_to(DATA_DIR).as_posix()
    digest = hashlib.sha256(path_file.read_bytes()).hexdigest()
    hasil[rel] = digest
  return hasil


def full_backup():
  """Menyalin seluruh isi folder data_latihan ke folder backup baru."""
  if not cek_mount("FULL_BACKUP", "data_latihan"):
    return

  if peran_aktif != "owner":
    print(
        "\n[DITOLAK] Hanya peran 'owner' yang dapat menjalankan Full Backup."
    )
    catat_log("FULL_BACKUP", "data_latihan", "DITOLAK (IZIN_AKSES)")
    return

  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  nama_backup = f"full_{timestamp}"
  tujuan = BACKUP_DIR / nama_backup

  shutil.copytree(DATA_DIR, tujuan)
  STATE_FILE.write_text(
      json.dumps(hitung_hash_semua_file(), indent=2), encoding="utf-8"
  )

  print(f"\n[BERHASIL] Full backup berhasil dibuat: backup/{nama_backup}")
  catat_log("FULL_BACKUP", nama_backup, "BERHASIL")


def incremental_backup():
  """Fitur bonus: Menyalin hanya file baru atau berubah sejak backup terakhir."""
  if not cek_mount("INCREMENTAL_BACKUP", "data_latihan"):
    return

  if peran_aktif != "owner":
    print(
        "\n[DITOLAK] Hanya peran 'owner' yang dapat menjalankan Incremental"
        " Backup."
    )
    catat_log("INCREMENTAL_BACKUP", "data_latihan", "DITOLAK (IZIN_AKSES)")
    return

  hash_sebelumnya = {}
  if STATE_FILE.exists():
    hash_sebelumnya = json.loads(STATE_FILE.read_text(encoding="utf-8"))

  hash_sekarang = hitung_hash_semua_file()
  file_berubah = [
      rel
      for rel, h in hash_sekarang.items()
      if hash_sebelumnya.get(rel) != h
  ]

  if not file_berubah:
    print(
        "\n[INFO] Tidak ada file baru atau perubahan sejak backup terakhir."
    )
    catat_log("INCREMENTAL_BACKUP", "data_latihan", "TIDAK_ADA_PERUBAHAN")
    return

  timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
  nama_backup = f"incremental_{timestamp}"
  tujuan = BACKUP_DIR / nama_backup
  tujuan.mkdir(parents=True, exist_ok=True)

  for rel in file_berubah:
    src = DATA_DIR / rel
    dst = tujuan / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

  STATE_FILE.write_text(json.dumps(hash_sekarang, indent=2), encoding="utf-8")
  print(
      f"\n[BERHASIL] Incremental backup dibuat: backup/{nama_backup}"
      f" ({len(file_berubah)} file disalin)"
  )
  for rel in file_berubah:
    print(f"  - {rel}")
  catat_log("INCREMENTAL_BACKUP", nama_backup, "BERHASIL")


def restore_backup():
  """Mengembalikan isi data_latihan dari folder backup yang dipilih."""
  if not cek_mount("RESTORE_BACKUP", "data_latihan"):
    return

  if peran_aktif != "owner":
    print("\n[DITOLAK] Hanya peran 'owner' yang dapat melakukan Restore.")
    catat_log("RESTORE_BACKUP", "data_latihan", "DITOLAK (IZIN_AKSES)")
    return

  daftar_backup = sorted([d for d in BACKUP_DIR.iterdir() if d.is_dir()])
  if not daftar_backup:
    print(
        "\n[GAGAL] Belum ada salinan backup. Jalankan Full Backup terlebih"
        " dahulu."
    )
    catat_log("RESTORE_BACKUP", "backup", "GAGAL (KOSONG)")
    return

  print("\nDaftar Salinan Backup Tersedia:")
  for idx, folder in enumerate(daftar_backup, start=1):
    print(f"  {idx}. {folder.name}")

  pilihan = input("Pilih nomor backup yang akan di-restore: ").strip()
  if not pilihan.isdigit() or not (1 <= int(pilihan) <= len(daftar_backup)):
    print("\n[GAGAL] Pilihan nomor backup tidak valid.")
    return

  sumber_backup = daftar_backup[int(pilihan) - 1]
  konfirmasi = (
      input(
          f"Data latihan saat ini akan ditimpa oleh '{sumber_backup.name}'."
          " Lanjutkan? (y/n): "
      )
      .strip()
      .lower()
  )
  if konfirmasi != "y":
    print("\n[DIBATALKAN] Proses restore dibatalkan.")
    catat_log("RESTORE_BACKUP", sumber_backup.name, "DIBATALKAN")
    return

  if sumber_backup.name.startswith("full_"):
    if DATA_DIR.exists():
      shutil.rmtree(DATA_DIR)
    shutil.copytree(sumber_backup, DATA_DIR)
    for kategori in KATEGORI_FOLDER:
      (DATA_DIR / kategori).mkdir(parents=True, exist_ok=True)
  else:
    # Untuk incremental backup, timpa file yang tercatat di dalamnya
    for src in sumber_backup.rglob("*.txt"):
      rel = src.relative_to(sumber_backup)
      dst = DATA_DIR / rel
      dst.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(src, dst)

  print(
      "\n[BERHASIL] Data latihan berhasil dipulihkan dari"
      f" '{sumber_backup.name}'."
  )
  catat_log("RESTORE_BACKUP", sumber_backup.name, "BERHASIL")


def tampilkan_log():
  """Menampilkan isi berkas aktivitas.log ke layar terminal."""
  print("\n=== LOG AKTIVITAS SISTEM ===")
  if not LOG_FILE.exists():
    print("(Belum ada catatan aktivitas)")
  else:
    print(LOG_FILE.read_text(encoding="utf-8").rstrip())
  print("============================")


def main():
  inisialisasi_lingkungan()
  while True:
    status_str = "MOUNTED" if is_mounted else "UNMOUNTED"
    print("\n====================================================")
    print("   APLIKASI SIMULASI SISTEM BERKAS ORGANISASI")
    print("====================================================")
    print(f"Status Storage : {status_str}")
    print(f"Peran Aktif    : {peran_aktif}")
    print("----------------------------------------------------")
    print("[1]  Mount / Unmount Storage")
    print("[2]  Ganti Peran (owner / anggota / tamu)")
    print("[3]  Lihat Daftar File")
    print("[4]  Baca File (.txt)")
    print("[5]  Buat File Baru (.txt)")
    print("[6]  Edit / Perbarui File (.txt)")
    print("[7]  Hapus File (.txt)")
    print("[8]  Full Backup")
    print("[9]  Incremental Backup (Bonus)")
    print("[10] Restore dari Backup")
    print("[11] Lihat Log Aktivitas")
    print("[0]  Keluar")
    print("----------------------------------------------------")

    pilihan = input("Pilih menu: ").strip()

    if pilihan == "1":
      toggle_mount()
    elif pilihan == "2":
      ganti_peran()
    elif pilihan == "3":
      lihat_daftar_file()
    elif pilihan == "4":
      baca_file()
    elif pilihan == "5":
      buat_file()
    elif pilihan == "6":
      edit_file()
    elif pilihan == "7":
      hapus_file()
    elif pilihan == "8":
      full_backup()
    elif pilihan == "9":
      incremental_backup()
    elif pilihan == "10":
      restore_backup()
    elif pilihan == "11":
      tampilkan_log()
    elif pilihan == "0":
      print("\nProgram selesai. Terima kasih.")
      break
    else:
      print("\n[GAGAL] Menu tidak tersedia. Masukkan angka 0 sampai 11.")


if __name__ == "__main__":
  main()