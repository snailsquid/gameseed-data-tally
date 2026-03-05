"""
process.py — Transform GAMESEED source CSVs into the 5 output CSVs.

Usage:
    python process.py <YEAR> [--dry-run] [--clean]

Arguments:
    YEAR        The edition year (e.g. 2025). Reads config/YEAR.yaml and
                sources/student{YEAR}.csv, sources/public{YEAR}.csv,
                plus any top files defined in the config tops: list.

Flags:
    --dry-run   Print row counts and samples without writing any files.
    --clean     Remove this year's rows from all output CSVs (undo a run).

Output CSVs (appended, fixed schema):
    participant.csv   — Nama Lengkap, Email, Discord Username, Nomor Whatsapp,
                        Asal Provinsi, Asal Kota, Jenis Kelamin, Tahun
    registration.csv  — Nama Lengkap, Nama Tim, Submitted at, Tahun, Category,
                        Pengalaman, Bukti Upload Konten
    team.csv          — Nama Tim, Kegiatan, Tahun
    student.csv       — Nama Lengkap, Status Studi, Institusi, Nomor Identifikasi,
                        Jurusan, Bukti Foto Kartu Tanda Mahasiswa / Kartu Pelajar, Tahun
    public.csv        — Nama Lengkap, Pekerjaan (boleh lebih dari 1),
                        Status Pekerjaan, Institusi (boleh lebih dari 1), Tahun
"""

import sys
import os
import yaml
import pandas as pd

# ---------------------------------------------------------------------------
# Fixed output schemas — these never change regardless of source column changes
# ---------------------------------------------------------------------------

OUTPUT_DIR = "output"

OUTPUT_SCHEMAS = {
    "participant.csv": [
        "Nama Lengkap", "Email", "Discord Username", "Nomor Whatsapp",
        "Asal Provinsi", "Asal Kota", "Jenis Kelamin", "Tahun",
    ],
    "registration.csv": [
        "Nama Lengkap", "Nama Tim", "Submitted at", "Tahun",
        "Category", "Pengalaman", "Bukti Upload Konten",
    ],
    "team.csv": ["Nama Tim", "Kegiatan", "Tahun"],
    "student.csv": [
        "Nama Lengkap", "Status Studi", "Institusi", "Nomor Identifikasi",
        "Jurusan", "Bukti Foto Kartu Tanda Mahasiswa / Kartu Pelajar", "Tahun",
    ],
    "public.csv": [
        "Nama Lengkap", "Pekerjaan (boleh lebih dari 1)",
        "Status Pekerjaan", "Institusi (boleh lebih dari 1)", "Tahun",
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_config(year: int) -> dict:
    path = os.path.join("config", f"{year}.yaml")
    if not os.path.exists(path):
        print(f"[ERR] Config file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def resolve_columns(df: pd.DataFrame, section: dict, source_label: str) -> tuple[pd.DataFrame, list[str]]:
    """
    For each canonical → {source, required} mapping in `section`, check whether
    the source column exists in df.

    - Required and missing  → collected as errors (caller will abort)
    - Optional and missing  → column added as NaN, warning printed
    - Found                 → column renamed to canonical name

    Returns:
        (df_resolved, errors)  where errors is a list of error strings.
    """
    errors = []
    warnings = []
    renames = {}   # source_col → canonical
    missing_optional = []

    actual_cols = list(df.columns)

    for canonical, spec in section.items():
        src = spec["source"]
        required = spec.get("required", False)

        if src in actual_cols:
            renames[src] = canonical
        else:
            if required:
                errors.append(
                    f"  [ERR]  {canonical:<20} → {src!r} (REQUIRED, not found in {source_label})"
                )
            else:
                warnings.append(
                    f"  [WARN] {canonical:<20} → {src!r} (optional, not found — filling with empty)"
                )
                missing_optional.append(canonical)

    # Print status for each mapping
    for canonical, spec in section.items():
        src = spec["source"]
        required = spec.get("required", False)
        tag = "required" if required else "optional"
        if src in actual_cols:
            print(f"  [OK]   {canonical:<20} → {src!r}")
        elif required:
            print(f"  [ERR]  {canonical:<20} → {src!r}  ← REQUIRED, not found")
        else:
            print(f"  [WARN] {canonical:<20} → {src!r}  ← optional, not found")

    # Apply renames and add missing optional columns as NaN
    df = df.rename(columns=renames)
    for col in missing_optional:
        df[col] = pd.NA

    return df, errors


def load_source(path: str, shared: dict, specific: dict, label: str) -> tuple[pd.DataFrame | None, bool]:
    """
    Load a source CSV, merge shared + specific column mappings (specific takes
    precedence), resolve columns and return the renamed DataFrame.

    Returns (df, ok) — ok=False means required columns were missing.
    """
    if not os.path.exists(path):
        print(f"[ERR] Source file not found: {path}")
        return None, False

    df = pd.read_csv(path)
    print(f"\n  Loaded {path}  ({len(df)} rows, {len(df.columns)} columns)")

    # Merge shared + specific mappings; specific overrides shared on same key
    merged = {**shared, **specific}

    df, errors = resolve_columns(df, merged, label)

    if errors:
        print(f"\n  The following REQUIRED columns are missing from {path}:")
        for e in errors:
            print(e)
        print(f"\n  Available columns in {path}:")
        for col in pd.read_csv(path, nrows=0).columns:
            print(f"    {col!r}")
        return None, False

    return df, True


def load_top_files(tops_config: list, year: int) -> list:
    """
    Load top files defined in the config tops: list.

    Each entry in tops_config must have:
        file:     filename inside sources/ (e.g. "igdx_2025.csv")
        kegiatan: value to write into the Kegiatan column (e.g. "IGDX")

    Returns a list of DataFrames, each with columns [Nama Tim, Kegiatan, Tahun].
    Missing or malformed files produce a [WARN] and are skipped.
    """
    if not tops_config:
        print("  [WARN] No tops entries defined in config — team.csv will only have Registered rows.")
        return []

    results = []
    for entry in tops_config:
        filename = entry.get("file")
        kegiatan = entry.get("kegiatan")

        if not filename or not kegiatan:
            print(f"  [WARN] Skipping malformed tops entry (missing 'file' or 'kegiatan'): {entry}")
            continue

        path = os.path.join("sources", filename)
        if not os.path.exists(path):
            print(f"  [WARN] {path} not found — skipping ({kegiatan})")
            continue

        df = pd.read_csv(path)
        if "Nama Tim" not in df.columns:
            print(f"  [WARN] 'Nama Tim' column not found in {path} — skipping ({kegiatan})")
            continue

        df = df[["Nama Tim"]].copy()
        df["Nama Tim"] = df["Nama Tim"].str.strip().str.lower()
        df["Kegiatan"] = kegiatan
        df["Tahun"] = year
        print(f"  [OK]   {path}  ({len(df)} rows)  kegiatan={kegiatan!r}")
        results.append(df)

    return results


def make_incubation_streak() -> pd.DataFrame:
    """
    Find people who were part of an Incubation team in two consecutive years.

    Logic:
      1. Filter team.csv for Kegiatan == "Incubation" -> (Nama Tim, Tahun) pairs
      2. Join registration.csv on Nama Tim + Tahun -> (Nama Lengkap, Nama Tim, Tahun)
      3. Self-join on Nama Lengkap (case-insensitive) where Tahun_2 == Tahun_1 + 1
      4. Return one row per person per consecutive pair, sorted by name then year

    Output columns:
        Nama Lengkap, Tahun 1, Nama Tim 1, Tahun 2, Nama Tim 2
    """
    team_path = os.path.join(OUTPUT_DIR, "team.csv")
    reg_path  = os.path.join(OUTPUT_DIR, "registration.csv")

    if not os.path.exists(team_path) or not os.path.exists(reg_path):
        print("  [WARN] team.csv or registration.csv not found — skipping incubation streak")
        return pd.DataFrame(columns=["Nama Lengkap", "Tahun 1", "Nama Tim 1", "Tahun 2", "Nama Tim 2"])

    team = pd.read_csv(team_path)
    reg  = pd.read_csv(reg_path)

    # Step 1: get all (Nama Tim, Tahun) pairs that reached Incubation
    incubation_teams = team[team["Kegiatan"] == "Incubation"][["Nama Tim", "Tahun"]].drop_duplicates()

    if incubation_teams.empty:
        print("  [INFO] No Incubation teams found in team.csv")
        return pd.DataFrame(columns=["Nama Lengkap", "Tahun 1", "Nama Tim 1", "Tahun 2", "Nama Tim 2"])

    # Step 2: join with registration to get the people in those teams
    people = reg.merge(incubation_teams, on=["Nama Tim", "Tahun"], how="inner")
    people = people[["Nama Lengkap", "Nama Tim", "Tahun"]].drop_duplicates()

    # Step 3: normalise name for cross-year matching
    people = people.copy()
    people["_name_key"] = people["Nama Lengkap"].str.strip().str.lower()

    # Self-join: left = year Y, right = year Y+1, matched on normalised name
    left  = people.rename(columns={"Tahun": "Tahun 1", "Nama Tim": "Nama Tim 1", "Nama Lengkap": "Nama Lengkap 1"})
    right = people.rename(columns={"Tahun": "Tahun 2", "Nama Tim": "Nama Tim 2", "Nama Lengkap": "Nama Lengkap 2"})

    merged = left.merge(right, on="_name_key")
    streak = merged[merged["Tahun 2"] == merged["Tahun 1"] + 1].copy()

    if streak.empty:
        return pd.DataFrame(columns=["Nama Lengkap", "Tahun 1", "Nama Tim 1", "Tahun 2", "Nama Tim 2"])

    # Use the name from the earlier year as canonical display name
    streak["Nama Lengkap"] = streak["Nama Lengkap 1"]
    streak = streak[["Nama Lengkap", "Tahun 1", "Nama Tim 1", "Tahun 2", "Nama Tim 2"]]
    streak = streak.sort_values(["Nama Lengkap", "Tahun 1"]).reset_index(drop=True)

    return streak


def append_to_output(fname: str, df_new: pd.DataFrame, year: int, dry_run: bool):
    """
    If the output CSV exists, remove existing rows for this year then append.
    If it doesn't exist, create it. Always enforces the fixed schema.
    """
    path = os.path.join(OUTPUT_DIR, fname)
    schema = OUTPUT_SCHEMAS[fname]

    # Ensure df_new has exactly the right columns in the right order
    for col in schema:
        if col not in df_new.columns:
            df_new[col] = pd.NA
    df_new = df_new[schema]

    if os.path.exists(path):
        df_existing = pd.read_csv(path)
        # Drop rows belonging to this year (safe re-run)
        df_existing = df_existing[df_existing["Tahun"] != year]
        df_out = pd.concat([df_existing, df_new], ignore_index=True)
    else:
        df_out = df_new

    if not dry_run:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        df_out.to_csv(path, index=False)

    return len(df_new), len(df_out)


def clean_year(year: int):
    """Remove all rows for `year` from every output CSV."""
    for fname in OUTPUT_SCHEMAS:
        path = os.path.join(OUTPUT_DIR, fname)
        if not os.path.exists(path):
            print(f"  [SKIP] {path} does not exist")
            continue
        df = pd.read_csv(path)
        before = len(df)
        df = df[df["Tahun"] != year]
        after = len(df)
        df.to_csv(path, index=False)
        print(f"  [OK]   {path}: removed {before - after} rows for {year} ({after} remaining)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python process.py <YEAR> [--dry-run] [--clean]")
        sys.exit(1)

    year_str = args[0]
    dry_run = "--dry-run" in args
    clean = "--clean" in args

    try:
        year = int(year_str)
    except ValueError:
        print(f"[ERR] YEAR must be an integer, got: {year_str!r}")
        sys.exit(1)

    # --- Clean mode ---
    if clean:
        print(f"Removing {year} data from all output CSVs...")
        clean_year(year)
        return

    if dry_run:
        print(f"=== DRY RUN — no files will be written ===\n")

    print(f"=== GAMESEED {year} Processing ===\n")

    config = load_config(year)
    mode = config.get("mode", "separate")

    shared = config.get("shared", {})
    student_specific = config.get("student", {})
    public_specific = config.get("public", {})
    tops_config = config.get("tops", [])

    # --- Check prerequisites ---
    student_path = os.path.join("sources", f"student{year}.csv")
    public_path = os.path.join("sources", f"public{year}.csv")

    if mode == "combined":
        combined_path = os.path.join("sources", f"gameseed{year}.csv")
        missing_split = not os.path.exists(student_path) or not os.path.exists(public_path)
        if missing_split:
            if os.path.exists(combined_path):
                print(f"[ERR] Mode is 'combined' but split files are missing.")
                print(f"      Run: python split.py {year}")
            else:
                print(f"[ERR] Mode is 'combined' but neither split files nor {combined_path} found.")
                print(f"      Place sources/gameseed{year}.csv then run: python split.py {year}")
            sys.exit(1)

    # --- Load sources ---
    print("--- Loading student source ---")
    df_s, ok_s = load_source(student_path, shared, student_specific, f"student{year}.csv")

    print("\n--- Loading public source ---")
    df_p, ok_p = load_source(public_path, shared, public_specific, f"public{year}.csv")

    if not ok_s or not ok_p:
        print("\n[ERR] Aborting due to missing required columns. Fix config or source files.")
        sys.exit(1)

    print("\n--- Loading top files ---")
    top_dfs = load_top_files(tops_config, year)

    # --- Clean & normalise ---
    for df in [df_s, df_p]:
        df["nama_lengkap"] = df["nama_lengkap"].str.strip().str.title()
        df["nama_tim"] = df["nama_tim"].str.strip().str.lower()

    # --- Build output DataFrames ---

    # participant.csv
    def make_participant(df, year):
        out = pd.DataFrame()
        out["Nama Lengkap"]      = df["nama_lengkap"]
        out["Email"]             = df.get("email", pd.NA)
        out["Discord Username"]  = df.get("discord", pd.NA)
        out["Nomor Whatsapp"]    = df.get("whatsapp", pd.NA)
        out["Asal Provinsi"]     = df.get("provinsi", pd.NA)
        out["Asal Kota"]         = df.get("kota", pd.NA)
        out["Jenis Kelamin"]     = df.get("gender", pd.NA)
        out["Tahun"]             = year
        return out

    df_participant = pd.concat(
        [make_participant(df_p, year), make_participant(df_s, year)],
        ignore_index=True,
    )

    # registration.csv
    def make_registration(df, category, year):
        out = pd.DataFrame()
        out["Nama Lengkap"]       = df["nama_lengkap"]
        out["Nama Tim"]           = df["nama_tim"]
        out["Submitted at"]       = df.get("submitted_at", pd.NA)
        out["Tahun"]              = year
        out["Category"]           = category
        out["Pengalaman"]         = df.get("pengalaman", pd.NA)
        out["Bukti Upload Konten"] = df.get("bukti_konten", pd.NA)
        return out

    df_registration = pd.concat(
        [make_registration(df_p, "Public", year), make_registration(df_s, "Student", year)],
        ignore_index=True,
    )
    df_registration = df_registration.drop_duplicates(subset=["Nama Lengkap", "Tahun"], keep="last")

    # team.csv
    def make_team(df, kegiatan, year):
        out = pd.DataFrame()
        out["Nama Tim"] = df["nama_tim"] if "nama_tim" in df.columns else df["Nama Tim"]
        out["Kegiatan"] = kegiatan
        out["Tahun"]    = year
        return out

    df_team = pd.concat(
        [
            make_team(df_p, "Registered", year),
            make_team(df_s, "Registered", year),
        ] + top_dfs,
        ignore_index=True,
    )
    df_team = df_team.drop_duplicates()

    # student.csv
    df_student_out = pd.DataFrame()
    df_student_out["Nama Lengkap"]    = df_s["nama_lengkap"]
    df_student_out["Status Studi"]    = df_s.get("status_studi", pd.NA)
    df_student_out["Institusi"]       = df_s.get("institusi", pd.NA)
    df_student_out["Nomor Identifikasi"] = df_s.get("nomor_id", pd.NA)
    df_student_out["Jurusan"]         = df_s.get("jurusan", pd.NA)
    df_student_out["Bukti Foto Kartu Tanda Mahasiswa / Kartu Pelajar"] = df_s.get("bukti_ktm", pd.NA)
    df_student_out["Tahun"]           = year

    # public.csv
    df_public_out = pd.DataFrame()
    df_public_out["Nama Lengkap"]                  = df_p["nama_lengkap"]
    df_public_out["Pekerjaan (boleh lebih dari 1)"] = df_p.get("pekerjaan", pd.NA)
    df_public_out["Status Pekerjaan"]              = df_p.get("status_pekerjaan", pd.NA)
    df_public_out["Institusi (boleh lebih dari 1)"] = df_p.get("institusi", pd.NA)
    df_public_out["Tahun"]                         = year

    # --- Summary ---
    outputs = {
        "participant.csv":  df_participant,
        "registration.csv": df_registration,
        "team.csv":         df_team,
        "student.csv":      df_student_out,
        "public.csv":       df_public_out,
    }

    print(f"\n--- Output preview ---")
    for fname, df in outputs.items():
        print(f"\n  {fname}  ({len(df)} new rows)")
        print(df.head(3).to_string(index=False))

    if dry_run:
        # --- Incubation streak preview (dry-run) ---
        print("\n--- Incubation streak preview ---")
        df_streak = make_incubation_streak()
        if df_streak.empty:
            print("  (no consecutive Incubation streaks found across accumulated years)")
        else:
            print(f"  incubation_streak.csv  ({len(df_streak)} rows)")
            print(df_streak.to_string(index=False))
        print("\n=== DRY RUN complete — no files written ===")
        return

    # --- Write outputs ---
    print(f"\n--- Writing outputs to {OUTPUT_DIR}/ ---")
    for fname, df_new in outputs.items():
        new_rows, total_rows = append_to_output(fname, df_new, year, dry_run=False)
        print(f"  [OK]   {OUTPUT_DIR}/{fname}: +{new_rows} rows  ({total_rows} total)")

    # --- Incubation streak (fully recomputed from all accumulated years) ---
    print("\n--- Computing incubation streak ---")
    df_streak = make_incubation_streak()
    streak_path = os.path.join(OUTPUT_DIR, "incubation_streak.csv")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_streak.to_csv(streak_path, index=False)
    print(f"  [OK]   {streak_path}: {len(df_streak)} rows")

    print(f"\n=== Done ===")
    print(f"  To undo: python process.py {year} --clean")


if __name__ == "__main__":
    main()
