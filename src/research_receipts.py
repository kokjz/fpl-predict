"""Explicitly scoped, write-once research receipts; no imported output roots."""
from pathlib import Path
import json


def receipt_path(evidence_directory, path):
    root = Path(evidence_directory).resolve(strict=True)
    target = Path(path)
    target = (root/target if not target.is_absolute() else target).resolve()
    if target == root or not target.is_relative_to(root):
        raise ValueError('Receipt escapes active evidence directory')
    return target


def write_bytes(evidence_directory, path, content):
    target = receipt_path(evidence_directory, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(content)
    return target


def write_json(evidence_directory, path, value):
    return write_bytes(evidence_directory, path,
                       (json.dumps(value, indent=2, allow_nan=False)+'\n').encode('utf-8'))
