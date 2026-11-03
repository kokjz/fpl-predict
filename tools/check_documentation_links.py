"""Check local Markdown/HTML links in explicitly named repository documents."""
import argparse
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


def check(paths):
    checked = 0
    errors = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        # Ignore fenced examples; allow links wrapped across Markdown lines.
        source = re.sub(r"```.*?```", "", source, flags=re.S)
        links = re.findall(r"\]\(([^\s)]+)(?:\s+[^)]*)?\)", source)
        links += re.findall(r'(?:src|href)="([^"]+)"', source)
        for link in links:
            parts = urlsplit(link)
            if parts.scheme or parts.netloc:
                continue
            target = (path.parent / unquote(parts.path)).resolve() if parts.path else path.resolve()
            checked += 1
            if not target.is_file():
                errors.append(f"{path}: missing {link}")
                continue
            if parts.fragment and target.suffix.lower() == ".md":
                headings = re.findall(r"^#{1,6}\s+(.+?)\s*#*\s*$", target.read_text(encoding="utf-8"), re.M)
                anchors = {re.sub(r"[^\w\- ]", "", h.lower()).replace(" ", "-") for h in headings}
                if unquote(parts.fragment) not in anchors:
                    errors.append(f"{path}: missing heading {link}")
    return checked, errors


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", type=Path, nargs="+")
    args = parser.parse_args()
    count, errors = check(args.paths)
    for error in errors:
        print(error)
    print(f"Checked {count} relative links; {len(errors)} errors.")
    raise SystemExit(bool(errors))
