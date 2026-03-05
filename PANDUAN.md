# Panduan GAMESEED Data Processing

Dokumen ini menjelaskan cara menggunakan skrip pemrosesan data GAMESEED dari awal hingga akhir. Tidak perlu pengalaman coding — cukup ikuti langkah-langkahnya.

---

## Daftar Isi

1. [Gambaran Umum](#1-gambaran-umum)
2. [Struktur Folder](#2-struktur-folder)
3. [Persiapan Awal](#3-persiapan-awal)
4. [Alur Kerja Tiap Tahun](#4-alur-kerja-tiap-tahun)
   - [Langkah 1 — Siapkan file sumber](#langkah-1--siapkan-file-sumber)
   - [Langkah 2 — Buat file konfigurasi](#langkah-2--buat-file-konfigurasi)
   - [Langkah 3 — Pisahkan data (jika satu file gabungan)](#langkah-3--pisahkan-data-jika-satu-file-gabungan)
   - [Langkah 4 — Proses data](#langkah-4--proses-data)
5. [File Konfigurasi](#5-file-konfigurasi)
6. [Memahami Pesan di Terminal](#6-memahami-pesan-di-terminal)
7. [Hasil Output](#7-hasil-output)
8. [Skenario Umum](#8-skenario-umum)
9. [Jika Ada Masalah](#9-jika-ada-masalah)

---

## 1. Gambaran Umum

Setiap tahun GAMESEED menerima data pendaftaran dari Tally (form online). Data mentah ini perlu dirapikan dan digabungkan ke dalam 5 file CSV yang dipakai oleh tim:

| File output | Isi |
|---|---|
| `participant.csv` | Data kontak semua peserta |
| `registration.csv` | Data pendaftaran per peserta per tim |
| `team.csv` | Daftar tim beserta status kegiatan (Registered / Incubation / IGDX) |
| `student.csv` | Data khusus peserta kategori Student |
| `public.csv` | Data khusus peserta kategori Public |
| `incubation_streak.csv` | Peserta yang masuk Incubation dua tahun berturut-turut |

File-file ini **terakumulasi** — data 2025 dan 2026 ada di file yang sama, dibedakan oleh kolom `Tahun`.

Ada dua skrip utama:

- **`split.py`** — memisahkan satu file gabungan menjadi file Student dan Public terpisah (hanya dipakai jika Tally memberikan satu file).
- **`process.py`** — memproses file sumber dan menambahkan hasilnya ke 5 file output.

---

## 2. Struktur Folder

```
gameseed-data-tally/
│
├── split.py              ← Skrip pemisah (jalankan lebih dulu jika perlu)
├── process.py            ← Skrip pemrosesan utama
│
├── config/               ← Satu file konfigurasi per tahun
│   ├── 2025.yaml
│   └── 2026.yaml         ← Buat ini untuk tahun baru
│
├── sources/              ← Taruh semua file sumber di sini
│   ├── student2025.csv
│   ├── public2025.csv
│   ├── igdx_2025.csv
│   └── incubation_2025.csv
│
└── output/               ← File output (terakumulasi)
    ├── participant.csv
    ├── registration.csv
    ├── team.csv
    ├── student.csv
    ├── public.csv
    └── incubation_streak.csv
```

---

## 3. Persiapan Awal

### Download kode dan extract

Buka Releases terbaru lalu download `Source code.zip` kemudian extract

### Masukkan source

Tim internal telah diberikan data tahun 2025. Masukkan semua file dari source sebagaimana struktur telah sediakan

### Buka terminal di folder gameseed-data-tally

Di Windows: klik kanan di dalam folder gameseed-data-tally → **"Open in Terminal"** atau **"Open PowerShell window here"**.

Di Mac/Linux: buka Terminal, lalu ketik:
```bash
cd /path/ke/folder/GAMESEED
```

### Pastikan Python tersedia

Ketik perintah ini dan tekan Enter:
```bash
python --version
```

Jika muncul angka versi (misal `Python 3.14.3`), berarti sudah siap. Jika tidak, install Python dari [python.org](https://python.org).

### Pastikan library yang dibutuhkan tersedia

Skrip ini membutuhkan dua library Python: `pandas` dan `pyyaml`. Jika belum ada, install dengan:
```bash
pip install pandas pyyaml
```

---

## 4. Alur Kerja Tiap Tahun

### Langkah 1 — Siapkan file sumber

Download file dari Tally, lalu taruh di folder `sources/` dengan penamaan yang benar.

**Penamaan file wajib:**

| File | Nama di folder `sources/` |
|---|---|
| Data Student dari Tally | `student2026.csv` |
| Data Public dari Tally | `public2026.csv` |
| Data gabungan dari Tally | `gameseed2026.csv` |
| Daftar tim IGDX | `igdx_2026.csv` |
| Daftar tim Incubation | `incubation_2026.csv` |

> **Ganti `2026` dengan tahun yang sedang diproses.**

`igdx_2026.csv` dan `incubation_2026.csv` cukup berisi satu kolom bernama `Nama Tim`.

> **Nama file top bisa disesuaikan di konfigurasi.** Lihat bagian [File Konfigurasi](#5-file-konfigurasi) untuk menambah atau mengubah nama file dan label kegiatan.

---

### Langkah 2 — Buat file konfigurasi

File konfigurasi memberi tahu skrip di mana menemukan setiap kolom di file Tally, karena nama kolom bisa berubah setiap tahun.

**Cara paling mudah:** salin konfigurasi tahun lalu:

```bash
cp config/2025.yaml config/2026.yaml
```

Lalu buka `config/2026.yaml` dengan teks editor (Notepad, VS Code, dll.) dan sesuaikan. Lihat [bagian 5](#5-file-konfigurasi) untuk penjelasan lengkap.

Hal yang **wajib diperiksa** setiap tahun:
- Kolom upload bukti biasanya mengandung tahun, misal `"Upload Bukti Konten GAMESEED 2025"` → ganti menjadi `"Upload Bukti Konten GAMESEED 2026"`.
- Di bagian `tops:`, perbarui nama file agar sesuai tahun baru (misal `igdx_2025.csv` → `igdx_2026.csv`).
- Jika Tally memberikan satu file gabungan tahun ini, ubah `mode: separate` menjadi `mode: combined`.

---

### Langkah 3 — Pisahkan data (jika satu file gabungan)

> Lewati langkah ini jika Tally sudah memberi dua file terpisah (Student dan Public).

Jika Tally memberikan satu file `gameseed2026.csv` yang memuat semua peserta, jalankan:

```bash
python split.py 2026
```

Skrip akan membaca kolom kategori (misal `Kategori`) dan memisahkan baris Student ke `sources/student2026.csv` dan baris Public ke `sources/public2026.csv`.

**Coba dulu tanpa menyimpan:**
```bash
python split.py 2026 --dry-run
```

Ini hanya menampilkan jumlah baris yang akan dipisah tanpa membuat file apapun.

---

### Langkah 4 — Proses data

Setelah file Student dan Public tersedia di `sources/`, jalankan:

```bash
python process.py 2026
```

**Sangat disarankan: coba dulu sebelum menyimpan:**
```bash
python process.py 2026 --dry-run
```

Perintah `--dry-run` menampilkan preview lengkap — jumlah baris, sampel data, dan peringatan kolom — tanpa mengubah file apapun. Gunakan ini untuk memverifikasi semuanya benar sebelum menjalankan proses sesungguhnya.

**Menjalankan ulang aman:** jika kamu menjalankan `process.py 2026` dua kali, data tidak akan terduplikasi. Skrip secara otomatis menghapus data tahun 2026 yang sudah ada sebelum menambahkan yang baru.

**Membatalkan / menghapus data yang sudah diproses:**
```bash
python process.py 2026 --clean
```

---

## 5. File Konfigurasi

File konfigurasi ada di folder `config/` dan diberi nama sesuai tahun, misal `2025.yaml`.

Berikut contoh lengkap dengan penjelasan tiap bagian:

```yaml
# ---------------------------------------------------------------
# MODE
# "separate" = Tally memberi dua file terpisah (student + public)
# "combined" = Tally memberi satu file gabungan (perlu split.py)
# ---------------------------------------------------------------
mode: separate


# ---------------------------------------------------------------
# SPLIT (hanya dipakai jika mode: combined)
# Definisikan kolom dan nilai yang membedakan Student vs Public
# ---------------------------------------------------------------
split:
  category_column: "Kategori"   # nama kolom di CSV yang berisi kategori
  student_value: "Student"      # nilai untuk baris Student
  public_value: "Public"        # nilai untuk baris Public


# ---------------------------------------------------------------
# TOP FILES
#
# Daftar file yang isinya akan masuk ke team.csv dengan label
# Kegiatan tertentu. Tambah atau hapus entri sesuai kebutuhan.
#
#   file:     nama file di dalam folder sources/
#   kegiatan: nilai yang ditulis ke kolom Kegiatan di team.csv
#
# File yang tidak ditemukan akan dilewati dengan peringatan [WARN].
# ---------------------------------------------------------------
tops:
  - file: "igdx_2026.csv"          # ← ganti tahun di nama file
    kegiatan: "IGDX"
  - file: "incubation_2026.csv"    # ← ganti tahun di nama file
    kegiatan: "Incubation"
  # Tambahkan entri baru jika ada tier lain, contoh:
  # - file: "finalist_2026.csv"
  #   kegiatan: "Finalist"


# ---------------------------------------------------------------
# PEMETAAN KOLOM
#
# Setiap entri punya dua properti:
#   source:   nama kolom persis seperti di file CSV dari Tally
#             (termasuk spasi atau karakter aneh jika ada)
#   required: true  → skrip berhenti dengan error jika kolom tidak ada
#             false → kolom diisi kosong dan skrip tetap berjalan
# ---------------------------------------------------------------

# Kolom yang ada di KEDUA file (student dan public)
shared:
  nama_lengkap:
    source: "Nama Lengkap"
    required: true
  email:
    source: "Email "        # ada spasi di belakang — salin persis dari Tally
    required: true
  discord:
    source: "Discord Username"
    required: false
  whatsapp:
    source: "Nomor Whatsapp"
    required: false
  provinsi:
    source: "Asal Provinsi"
    required: false
  kota:
    source: "Asal Kota"
    required: false
  gender:
    source: "Jenis Kelamin"
    required: false
  submitted_at:
    source: "Submitted at"
    required: true
  pengalaman:
    source: "Pengalamanmu dalam Game Development"
    required: false

# Kolom khusus file Student
student:
  nama_tim:
    source: "Nama Tim"
    required: true
  bukti_konten:
    source: "Upload Bukti Konten GAMESEED 2025"   # ← ganti tahun ini
    required: false
  status_studi:
    source: "Status Studi"
    required: false
  institusi:
    source: "Institusi (boleh lebih dari 1)"
    required: false
  nomor_id:
    source: "Nomor Identifikasi di Institusi Pendidikan"
    required: false
  jurusan:
    source: "Jurusan"
    required: false
  bukti_ktm:
    source: "Bukti Foto Kartu Tanda Mahasiswa / Kartu Pelajar"
    required: false

# Kolom khusus file Public
public:
  nama_tim:
    source: "Nama Tim\n"    # ada karakter newline di belakang — ini normal untuk 2025
    required: true
  bukti_konten:
    source: "Upload Bukti Post Konten GAMESEED 2025"   # ← ganti tahun ini
    required: false
  pekerjaan:
    source: "Pekerjaan (boleh lebih dari 1)"
    required: false
  status_pekerjaan:
    source: "Status Pekerjaan"
    required: false
  institusi:
    source: "Institusi (boleh lebih dari 1)"
    required: false
```

### Tips memeriksa nama kolom yang benar

Jika tidak yakin nama kolom persis seperti apa, buka file CSV dengan Excel atau Google Sheets dan lihat baris pertama (header). Salin nama kolomnya persis termasuk spasi dan tanda baca, lalu tempel ke config.

---

## 6. Memahami Pesan di Terminal

Saat skrip berjalan, setiap kolom akan dilaporkan:

```
[OK]   nama_lengkap         → 'Nama Lengkap'
[OK]   email                → 'Email '
[WARN] jurusan              → 'Jurusan'  ← optional, not found
[ERR]  nama_tim             → 'Nama Tim'  ← REQUIRED, not found
```

| Tanda | Artinya | Yang perlu dilakukan |
|---|---|---|
| `[OK]` | Kolom ditemukan dan berhasil dipetakan | Tidak perlu apa-apa |
| `[WARN]` | Kolom tidak ditemukan, tapi tidak wajib — output akan kosong untuk kolom ini | Periksa apakah memang kolom ini tidak ada di Tally tahun ini, atau nama kolom berubah |
| `[ERR]` | Kolom tidak ditemukan dan **wajib ada** — skrip berhenti | Buka `config/{YEAR}.yaml` dan perbarui nilai `source:` sesuai nama kolom yang sebenarnya |

Jika ada `[ERR]`, skrip akan menampilkan daftar kolom yang tersedia di file CSV tersebut untuk membantu kamu menemukan nama yang benar:

```
Available columns in student2026.csv:
  'Nama Lengkap'
  'Email'
  'Nama Tim'
  ...
```

---

## 7. Hasil Output

Setelah `process.py` selesai, terminal menampilkan ringkasan seperti ini:

```
--- Writing outputs ---
  [OK]   participant.csv: +1779 rows  (1779 total)
  [OK]   registration.csv: +1649 rows  (1649 total)
  [OK]   team.csv: +475 rows  (475 total)
  [OK]   student.csv: +1145 rows  (1145 total)
  [OK]   public.csv: +634 rows  (634 total)
```

Angka di `+...` adalah baris baru yang ditambahkan tahun ini. Angka di `(... total)` adalah total seluruh baris di file termasuk tahun-tahun sebelumnya.

Setelah 5 file utama selesai, skrip secara otomatis menghitung dan menulis:

```
--- Computing incubation streak ---
  [OK]   output/incubation_streak.csv: 0 rows
```

`incubation_streak.csv` berisi satu baris per peserta yang tim-nya masuk Incubation di dua tahun **berturut-turut** (misal 2025 dan 2026). Kolom-nya:

| Kolom | Keterangan |
|---|---|
| `Nama Lengkap` | Nama peserta |
| `Tahun 1` | Tahun Incubation pertama |
| `Nama Tim 1` | Nama tim di tahun tersebut |
| `Tahun 2` | Tahun Incubation kedua (Tahun 1 + 1) |
| `Nama Tim 2` | Nama tim di tahun tersebut |

> File ini **dihitung ulang sepenuhnya** setiap kali `process.py` dijalankan — bukan ditambahkan seperti file lain. Jika baru ada data satu tahun, file ini akan berisi 0 baris, dan akan terisi ketika ada data tahun berikutnya.

---

## 8. Skenario Umum

### Skenario A: Tally memberikan dua file terpisah (seperti 2025)

```
File dari Tally:
  student2026.csv
  public2026.csv
  (file IGDX)        → rename menjadi igdx_2026.csv
  (file Incubation)  → rename menjadi incubation_2026.csv
```

```bash
# 1. Pindahkan file ke folder sources/ dengan nama yang benar

# 2. Buat konfigurasi
cp config/2025.yaml config/2026.yaml
# Edit config/2026.yaml:
#   - pastikan mode: separate
#   - update nama file di bagian tops: (ganti 2025 → 2026)
#   - update nama kolom yang berubah

# 3. Preview
python process.py 2026 --dry-run

# 4. Proses
python process.py 2026
```

---

### Skenario B: Tally memberikan satu file gabungan

```
File dari Tally:
  gameseed2026.csv  (berisi semua peserta dengan kolom Kategori)
  (file IGDX)        → rename menjadi igdx_2026.csv
  (file Incubation)  → rename menjadi incubation_2026.csv
```

```bash
# 1. Pindahkan file ke folder sources/ dengan nama yang benar
#    gameseed2026.csv, igdx_2026.csv, incubation_2026.csv

# 2. Buat konfigurasi
cp config/2025.yaml config/2026.yaml
# Edit config/2026.yaml:
#   - ubah mode: combined
#   - isi bagian split: sesuai kolom kategori di file Tally
#   - update nama file di bagian tops: (ganti 2025 → 2026)
#   - update nama kolom yang berubah

# 3. Pisahkan data
python split.py 2026 --dry-run   # cek dulu
python split.py 2026             # jalankan

# 4. Preview dan proses
python process.py 2026 --dry-run
python process.py 2026
```

---

### Skenario C: Ada kesalahan dan ingin mengulang dari awal

```bash
# Hapus data tahun ini dari semua output
python process.py 2026 --clean

# Perbaiki konfigurasi atau file sumber, lalu jalankan lagi
python process.py 2026
```

---

## 9. Jika Ada Masalah

### "Config file not found"

```
[ERR] Config file not found: config/2026.yaml
```

File konfigurasi belum dibuat. Jalankan:
```bash
cp config/2025.yaml config/2026.yaml
```
Lalu edit sesuai kebutuhan.

---

### "Source file not found"

```
[ERR] Source file not found: sources/student2026.csv
```

File sumber belum ada di folder `sources/` atau namanya salah. Pastikan nama file persis sesuai konvensi: `student{TAHUN}.csv`, `public{TAHUN}.csv`, `igdx_{TAHUN}.csv`, `incubation_{TAHUN}.csv`, dst. — atau sesuai yang didefinisikan di bagian `tops:` dalam config.

---

### "REQUIRED, not found" pada kolom tertentu

```
[ERR]  nama_tim  → 'Nama Tim'  ← REQUIRED, not found
```

Nama kolom di file CSV tidak cocok dengan yang ada di config. Skrip akan menampilkan daftar kolom yang tersedia — salin nama yang benar dan perbarui nilai `source:` di `config/2026.yaml`.

---

### "Run: python split.py 2026"

```
[ERR] Mode is 'combined' but split files are missing.
      Run: python split.py 2026
```

Config diset `mode: combined` tapi file `student2026.csv` dan `public2026.csv` belum ada. Jalankan `split.py` terlebih dahulu.

---

### Kolom output kosong untuk seluruh tahun ini

Ini terjadi jika kolom tersebut tidak ditemukan di file Tally dan ditandai `required: false`. Periksa apakah:
1. Kolom memang tidak ada di Tally tahun ini (normal).
2. Nama kolom berubah — buka CSV, cek header, perbarui config.
