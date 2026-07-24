"""
VM Tagger — bulk-tag VMs in Azure and AWS from a CSV/Excel input file.
GUI mode: python tagger.py
CLI mode: python tagger.py --input vms.csv [--dry-run]
"""

import argparse
import csv
import sys
import threading
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class TagRow:
    cloud: str                          # "azure" | "aws"
    subscription_or_account: str        # Azure subscription ID or AWS account ID
    resource_group_or_region: str       # Azure RG name or AWS region
    vm_name: str
    tag_key: str
    tag_value: str


@dataclass
class TagResult:
    row: TagRow
    success: bool
    message: str = ""


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def load_input(path: str) -> list[TagRow]:
    p = Path(path)
    if p.suffix.lower() in (".xlsx", ".xls"):
        return _load_excel(p)
    return _load_csv(p)


def _load_csv(path: Path) -> list[TagRow]:
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, record in enumerate(reader, start=2):
            row = _parse_record(record, i)
            if row:
                rows.append(row)
    return rows


def _load_excel(path: Path) -> list[TagRow]:
    if not HAS_OPENPYXL:
        raise ImportError("openpyxl is required for Excel files: pip install openpyxl")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    headers = None
    for i, row in enumerate(ws.iter_rows(values_only=True), start=1):
        if i == 1:
            headers = [str(c).strip().lower() if c else "" for c in row]
            continue
        record = dict(zip(headers, [str(c).strip() if c is not None else "" for c in row]))
        parsed = _parse_record(record, i + 1)
        if parsed:
            rows.append(parsed)
    wb.close()
    return rows


def _parse_record(record: dict, line: int) -> Optional[TagRow]:
    required = ["cloud", "subscription_or_account", "resource_group_or_region",
                "vm_name", "tag_key", "tag_value"]
    for col in required:
        if not record.get(col, "").strip():
            return None  # skip blank/incomplete rows
    return TagRow(
        cloud=record["cloud"].strip().lower(),
        subscription_or_account=record["subscription_or_account"].strip(),
        resource_group_or_region=record["resource_group_or_region"].strip(),
        vm_name=record["vm_name"].strip(),
        tag_key=record["tag_key"].strip(),
        tag_value=record["tag_value"].strip(),
    )


# ---------------------------------------------------------------------------
# Azure tagging
# ---------------------------------------------------------------------------

def tag_azure_vm(row: TagRow, dry_run: bool) -> TagResult:
    try:
        from azure.identity import DefaultAzureCredential
        from azure.mgmt.compute import ComputeManagementClient
    except ImportError:
        return TagResult(row, False, "azure-identity / azure-mgmt-compute not installed")

    if dry_run:
        return TagResult(row, True, f"[DRY-RUN] would tag {row.vm_name} → {row.tag_key}={row.tag_value}")

    try:
        credential = DefaultAzureCredential()
        client = ComputeManagementClient(credential, row.subscription_or_account)
        vm = client.virtual_machines.get(row.resource_group_or_region, row.vm_name)
        tags = vm.tags or {}
        tags[row.tag_key] = row.tag_value
        client.virtual_machines.begin_update(
            row.resource_group_or_region, row.vm_name, {"tags": tags}
        ).result()
        return TagResult(row, True, f"Tagged {row.vm_name} → {row.tag_key}={row.tag_value}")
    except Exception as exc:
        return TagResult(row, False, str(exc))


# ---------------------------------------------------------------------------
# AWS tagging
# ---------------------------------------------------------------------------

def tag_aws_vm(row: TagRow, dry_run: bool) -> TagResult:
    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError:
        return TagResult(row, False, "boto3 not installed")

    if dry_run:
        return TagResult(row, True, f"[DRY-RUN] would tag {row.vm_name} → {row.tag_key}={row.tag_value}")

    try:
        ec2 = boto3.client(
            "ec2",
            region_name=row.resource_group_or_region,
            # AWS account switching: assumes the calling identity has access.
            # For cross-account, set up AWS profiles or assume-role externally.
        )
        # Accept either instance ID (i-xxx) or Name tag lookup
        if row.vm_name.startswith("i-"):
            instance_ids = [row.vm_name]
        else:
            resp = ec2.describe_instances(
                Filters=[{"Name": "tag:Name", "Values": [row.vm_name]}]
            )
            instance_ids = [
                inst["InstanceId"]
                for res in resp["Reservations"]
                for inst in res["Instances"]
            ]
            if not instance_ids:
                return TagResult(row, False, f"No instance found with Name={row.vm_name}")

        ec2.create_tags(
            Resources=instance_ids,
            Tags=[{"Key": row.tag_key, "Value": row.tag_value}],
        )
        return TagResult(row, True, f"Tagged {row.vm_name} ({instance_ids}) → {row.tag_key}={row.tag_value}")
    except Exception as exc:
        return TagResult(row, False, str(exc))


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

def process_rows(rows: list[TagRow], dry_run: bool,
                 progress_cb=None) -> list[TagResult]:
    results = []
    for i, row in enumerate(rows):
        if row.cloud == "azure":
            result = tag_azure_vm(row, dry_run)
        elif row.cloud == "aws":
            result = tag_aws_vm(row, dry_run)
        else:
            result = TagResult(row, False, f"Unknown cloud: {row.cloud}")
        results.append(result)
        if progress_cb:
            progress_cb(i + 1, len(rows), result)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def run_cli(input_path: str, dry_run: bool):
    rows = load_input(input_path)
    print(f"Loaded {len(rows)} tag operations from {input_path}")
    if dry_run:
        print("DRY-RUN mode — no changes will be applied\n")

    ok = err = 0
    for i, row in enumerate(rows):
        if row.cloud == "azure":
            result = tag_azure_vm(row, dry_run)
        elif row.cloud == "aws":
            result = tag_aws_vm(row, dry_run)
        else:
            result = TagResult(row, False, f"Unknown cloud: {row.cloud}")

        status = "OK " if result.success else "ERR"
        print(f"[{status}] {row.cloud.upper():5s} {row.vm_name:40s} {result.message}")
        if result.success:
            ok += 1
        else:
            err += 1

    print(f"\nDone — {ok} succeeded, {err} failed")


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

def _import_tkinter():
    try:
        import tkinter as tk
        from tkinter import filedialog, scrolledtext, ttk
        return tk, filedialog, scrolledtext, ttk
    except ModuleNotFoundError:
        sys.exit(
            "Tkinter is not available in this Python installation.\n"
            "Install it (e.g. brew install python-tk) or use CLI mode:\n"
            "  python tagger.py --input vms.csv --dry-run"
        )


class TaggerApp:
    def __init__(self, root):
        self.root = root
        self._tk, self._filedialog, self._scrolledtext, self._ttk = _import_tkinter()
        root.title("VM Tagger")
        root.resizable(True, True)
        self._build_ui()

    def _build_ui(self):
        tk = self._tk
        ttk = self._ttk
        scrolledtext = self._scrolledtext
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(3, weight=1)

        # --- File picker row ---
        file_frame = ttk.Frame(root, padding=8)
        file_frame.grid(row=0, column=0, sticky="ew")
        file_frame.columnconfigure(1, weight=1)

        ttk.Label(file_frame, text="Input file:").grid(row=0, column=0, sticky="w")
        self.file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_var, width=60).grid(
            row=0, column=1, sticky="ew", padx=4)
        ttk.Button(file_frame, text="Browse…", command=self._browse).grid(
            row=0, column=2)

        # --- Options row ---
        opt_frame = ttk.Frame(root, padding=(8, 0, 8, 8))
        opt_frame.grid(row=1, column=0, sticky="ew")

        self.dry_run_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt_frame, text="Dry-run (preview only, no changes)",
                        variable=self.dry_run_var).grid(row=0, column=0, sticky="w")

        # --- Action buttons ---
        btn_frame = ttk.Frame(root, padding=(8, 0, 8, 8))
        btn_frame.grid(row=2, column=0, sticky="ew")

        self.run_btn = ttk.Button(btn_frame, text="Run", command=self._run)
        self.run_btn.grid(row=0, column=0, padx=(0, 6))
        ttk.Button(btn_frame, text="Clear log", command=self._clear_log).grid(row=0, column=1)

        self.progress = ttk.Progressbar(btn_frame, length=300, mode="determinate")
        self.progress.grid(row=0, column=2, padx=(12, 0))
        self.progress_label = ttk.Label(btn_frame, text="")
        self.progress_label.grid(row=0, column=3, padx=6)

        # --- Log area ---
        log_frame = ttk.LabelFrame(root, text="Log", padding=4)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=(0, 8))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = scrolledtext.ScrolledText(log_frame, height=20, wrap=tk.WORD,
                                             font=("Courier", 10))
        self.log.grid(row=0, column=0, sticky="nsew")
        self.log.tag_config("ok",  foreground="#1a9850")
        self.log.tag_config("err", foreground="#d73027")
        self.log.tag_config("dry", foreground="#4393c3")
        self.log.tag_config("info", foreground="#666666")

    def _browse(self):
        path = self._filedialog.askopenfilename(
            title="Select input file",
            filetypes=[("CSV / Excel", "*.csv *.xlsx *.xls"), ("All files", "*.*")],
        )
        if path:
            self.file_var.set(path)

    def _clear_log(self):
        self.log.delete("1.0", self._tk.END)

    def _log(self, message: str, tag: str = ""):
        self.log.insert(self._tk.END, message + "\n", tag)
        self.log.see(self._tk.END)

    def _run(self):
        path = self.file_var.get().strip()
        if not path:
            self._log("Please select an input file.", "err")
            return

        self.run_btn.config(state="disabled")
        self.progress["value"] = 0
        self.progress_label.config(text="")
        self._log(f"Loading {path} …", "info")

        threading.Thread(target=self._worker, args=(path,), daemon=True).start()

    def _worker(self, path: str):
        dry_run = self.dry_run_var.get()
        try:
            rows = load_input(path)
        except Exception as exc:
            self.root.after(0, self._log, f"Failed to load file: {exc}", "err")
            self.root.after(0, self.run_btn.config, {"state": "normal"})
            return

        self.root.after(0, self._log,
                        f"Loaded {len(rows)} operations. "
                        f"{'DRY-RUN — no changes will be applied.' if dry_run else 'LIVE mode.'}",
                        "dry" if dry_run else "info")

        ok = err = 0
        for i, row in enumerate(rows, 1):
            if row.cloud == "azure":
                result = tag_azure_vm(row, dry_run)
            elif row.cloud == "aws":
                result = tag_aws_vm(row, dry_run)
            else:
                result = TagResult(row, False, f"Unknown cloud: {row.cloud}")

            tag = "dry" if dry_run else ("ok" if result.success else "err")
            label = "[DRY]" if dry_run else ("[OK ]" if result.success else "[ERR]")
            msg = f"{label} {row.cloud.upper():5s} {row.vm_name:40s} {result.message}"
            self.root.after(0, self._log, msg, tag)

            if result.success:
                ok += 1
            else:
                err += 1

            pct = int(i / len(rows) * 100)
            self.root.after(0, self._set_progress, pct, f"{i}/{len(rows)}")

        summary = f"\nDone — {ok} succeeded, {err} failed"
        self.root.after(0, self._log, summary, "ok" if err == 0 else "err")
        self.root.after(0, self.run_btn.config, {"state": "normal"})

    def _set_progress(self, pct: int, label: str):
        self.progress["value"] = pct
        self.progress_label.config(text=label)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Bulk-tag VMs in Azure and AWS")
    parser.add_argument("--input", help="CSV or Excel input file (omit for GUI)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview operations without making changes")
    args = parser.parse_args()

    if args.input:
        run_cli(args.input, args.dry_run)
    else:
        tk, _fd, _st, _ttk = _import_tkinter()
        root = tk.Tk()
        app = TaggerApp(root)
        root.mainloop()


if __name__ == "__main__":
    main()
