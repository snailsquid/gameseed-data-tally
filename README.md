# GAMESEED Data Processing

Converts raw Tally form exports into clean, year-accumulating output CSVs.

## Directory structure

```
GAMESEED/
├── split.py              # Step 1 (if needed): split combined CSV into student + public
├── process.py            # Step 2: transform sources into output CSVs
├── config/
│   └── 2025.yaml         # Column mappings per year
├── sources/
│   ├── student{YEAR}.csv
│   ├── public{YEAR}.csv
│   ├── igdx_{YEAR}.csv
│   └── incubation_{YEAR}.csv
└── output/               # Output — accumulated across years
    ├── participant.csv
    ├── registration.csv
    ├── team.csv
    ├── student.csv
    ├── public.csv
    └── incubation_streak.csv
```

## Output schemas

| File | Columns |
|---|---|
| `participant.csv` | Nama Lengkap, Email, Discord Username, Nomor Whatsapp, Asal Provinsi, Asal Kota, Jenis Kelamin, Tahun |
| `registration.csv` | Nama Lengkap, Nama Tim, Submitted at, Tahun, Category, Pengalaman, Bukti Upload Konten |
| `team.csv` | Nama Tim, Kegiatan, Tahun |
| `student.csv` | Nama Lengkap, Status Studi, Institusi, Nomor Identifikasi, Jurusan, Bukti Foto Kartu Tanda Mahasiswa / Kartu Pelajar, Tahun |
| `public.csv` | Nama Lengkap, Pekerjaan (boleh lebih dari 1), Status Pekerjaan, Institusi (boleh lebih dari 1), Tahun |
| `incubation_streak.csv` | Nama Lengkap, Tahun 1, Nama Tim 1, Tahun 2, Nama Tim 2 |

Output schemas are fixed — missing source columns produce empty cells, they never cause a column to be dropped.

`incubation_streak.csv` is an exception: it is **fully recomputed** from all accumulated years every run (not appended), and is not affected by `--clean`. It contains one row per person per consecutive Incubation pair (e.g. 2025→2026). Identified by Nama Lengkap (case-insensitive). If only one year of data exists it will contain 0 rows.

## Workflow

### Each new year: create a config file

Copy last year's config and update it for the new year:

```bash
cp config/2025.yaml config/2026.yaml
```

Then edit `config/2026.yaml`:
- Set `mode` to `separate` or `combined` (see below)
- Update any column names that changed in the Tally export (e.g. year-stamped upload columns)
- Update the `tops:` filenames to match the new year (e.g. `igdx_2026.csv`)

### Source mode: `separate` (two files from Tally)

Tally gives you one file per category. Place them in `sources/` and skip `split.py`:

```
sources/student2026.csv
sources/public2026.csv
sources/igdx_2026.csv
sources/incubation_2026.csv
```

```bash
python process.py 2026 --dry-run   # preview without writing
python process.py 2026
```

### Source mode: `combined` (one file from Tally)

Tally gives you one combined file with a column that distinguishes Student from Public rows. Place it in `sources/` and run `split.py` first:

```
sources/gameseed2026.csv
sources/igdx_2026.csv
sources/incubation_2026.csv
```

```bash
python split.py 2026               # produces student2026.csv + public2026.csv
python process.py 2026 --dry-run   # preview without writing
python process.py 2026
```

## Config reference (`config/{YEAR}.yaml`)

```yaml
# "separate" = two source files already exist (student + public)
# "combined" = one gameseed{YEAR}.csv that needs splitting first
mode: separate

# Only used when mode is "combined"
split:
  category_column: "Kategori"      # column that holds the category value
  student_value: "Student"
  public_value: "Public"

# Top files — each entry becomes a set of rows in team.csv with the given Kegiatan value.
# file:     filename inside sources/ (just the name, not the full path)
# kegiatan: value written to the Kegiatan column in team.csv
# Add or remove entries freely. Missing files produce a [WARN] and are skipped.
tops:
  - file: "igdx_2026.csv"
    kegiatan: "IGDX"
  - file: "incubation_2026.csv"
    kegiatan: "Incubation"
  # - file: "finalist_2026.csv"   # add more tiers as needed
  #   kegiatan: "Finalist"

# Column mappings: canonical name → actual column header in the CSV
# required: true  → aborts with an error if the column is missing
# required: false → fills with empty and continues with a warning
shared:
  nama_lengkap:
    source: "Nama Lengkap"
    required: true
  email:
    source: "Email "               # trailing space common in Tally exports
    required: true
  # ... etc

student:
  bukti_konten:
    source: "Upload Bukti Konten GAMESEED 2026"   # update year here
    required: false
  # ... etc

public:
  nama_tim:
    source: "Nama Tim\n"           # newline sometimes embedded by Tally
    required: true
  # ... etc
```

`shared` keys apply to both student and public sources. Keys defined under `student` or `public` override shared keys for that source only.

## Script flags

### `process.py`

| Flag | Effect |
|---|---|
| *(none)* | Run normally — append new year's rows to output CSVs |
| `--dry-run` | Print row counts and samples, write nothing |
| `--clean` | Remove this year's rows from all outputs (undo) |

Re-running `process.py` for the same year is safe — it removes that year's rows before appending, so there are no duplicates.

### `split.py`

| Flag | Effect |
|---|---|
| *(none)* | Split combined CSV and write student + public files |
| `--dry-run` | Print row counts and samples, write nothing |

If `mode` is `separate` in the config, `split.py` exits immediately with no changes.

## Missing columns

When a source CSV is loaded, every mapped column is checked and reported:

```
[OK]   nama_lengkap         → 'Nama Lengkap'
[WARN] jurusan              → 'Jurusan'  ← optional, not found
[ERR]  nama_tim             → 'Nama Tim'  ← REQUIRED, not found
```

- `[OK]` — column found and mapped
- `[WARN]` — optional column missing; output column will be empty for this year
- `[ERR]` — required column missing; script aborts and lists the actual columns in the file so you can update the config

## Dependencies

- `pandas`
- `pyyaml`

Both must be available in the Python environment used to run the scripts.
