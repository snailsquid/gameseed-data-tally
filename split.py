"""
split.py — Split a combined GAMESEED source CSV into separate student and public files.

Usage:
    python split.py <YEAR> [--dry-run]

Arguments:
    YEAR        The edition year (e.g. 2026). Reads config/YEAR.yaml and
                sources/gameseedYEAR.csv. Writes sources/studentYEAR.csv and
                sources/publicYEAR.csv.

Flags:
    --dry-run   Print row counts and sample rows without writing any files.

Only needed when config mode is "combined". For "separate" mode years, the
student and public source files already exist and this script is a no-op.
"""

import sys
import os
import yaml
import pandas as pd


def load_config(year: int) -> dict:
    path = os.path.join("config", f"{year}.yaml")
    if not os.path.exists(path):
        print(f"[ERR] Config file not found: {path}")
        sys.exit(1)
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python split.py <YEAR> [--dry-run]")
        sys.exit(1)

    year_str = args[0]
    dry_run = "--dry-run" in args

    try:
        year = int(year_str)
    except ValueError:
        print(f"[ERR] YEAR must be an integer, got: {year_str!r}")
        sys.exit(1)

    config = load_config(year)
    mode = config.get("mode", "separate")

    if mode == "separate":
        print(f"[INFO] Config for {year} has mode='separate'. Sources are already split.")
        print(f"       sources/student{year}.csv and sources/public{year}.csv should exist.")
        sys.exit(0)

    if mode != "combined":
        print(f"[ERR] Unknown mode {mode!r} in config/{year}.yaml. Expected 'separate' or 'combined'.")
        sys.exit(1)

    # --- Combined mode ---
    source_path = os.path.join("sources", f"gameseed{year}.csv")
    if not os.path.exists(source_path):
        print(f"[ERR] Source file not found: {source_path}")
        sys.exit(1)

    split_cfg = config.get("split")
    if not split_cfg:
        print(f"[ERR] config/{year}.yaml has mode='combined' but no 'split:' section.")
        sys.exit(1)

    cat_col = split_cfg.get("category_column")
    student_val = split_cfg.get("student_value")
    public_val = split_cfg.get("public_value")

    if not all([cat_col, student_val, public_val]):
        print(f"[ERR] 'split' section in config/{year}.yaml must define "
              f"category_column, student_value, and public_value.")
        sys.exit(1)

    print(f"[INFO] Reading {source_path}...")
    df = pd.read_csv(source_path)
    total = len(df)

    if cat_col not in df.columns:
        print(f"[ERR] Category column {cat_col!r} not found in {source_path}.")
        print(f"      Available columns: {list(df.columns)}")
        sys.exit(1)

    df_student = df[df[cat_col] == student_val].reset_index(drop=True)
    df_public = df[df[cat_col] == public_val].reset_index(drop=True)

    n_student = len(df_student)
    n_public = len(df_public)
    n_other = total - n_student - n_public

    # Warn about rows that matched neither category value
    if n_other > 0:
        other_vals = df[~df[cat_col].isin([student_val, public_val])][cat_col].unique()
        print(f"[WARN] {n_other} row(s) had unexpected values in {cat_col!r}: {list(other_vals)}")
        print(f"       These rows will NOT be written to either output file.")

    print(f"\n  Total rows : {total}")
    print(f"  Student    : {n_student}  (value={student_val!r})")
    print(f"  Public     : {n_public}  (value={public_val!r})")

    if n_student > 0:
        print(f"\n  Student sample:")
        print(df_student.head(3).to_string(index=False))

    if n_public > 0:
        print(f"\n  Public sample:")
        print(df_public.head(3).to_string(index=False))

    if dry_run:
        print("\n[DRY RUN] No files written.")
        return

    student_out = os.path.join("sources", f"student{year}.csv")
    public_out = os.path.join("sources", f"public{year}.csv")

    df_student.to_csv(student_out, index=False)
    df_public.to_csv(public_out, index=False)

    print(f"\n[OK] Written: {student_out} ({n_student} rows)")
    print(f"[OK] Written: {public_out} ({n_public} rows)")
    print(f"\nNext step: python process.py {year}")


if __name__ == "__main__":
    main()
