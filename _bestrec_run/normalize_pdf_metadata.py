# -*- coding: utf-8 -*-
"""Normalize volatile PDF metadata without changing object offsets.

Edge and Tectonic/XeTeX embed wall-clock dates, XMP UUIDs, and trailer file
identifiers.  All replacements below are fixed-width, so cross-reference byte
offsets remain valid while release PDFs become byte-reproducible.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


_ZERO_UUID = b"00000000-0000-0000-0000-000000000000"


def normalize_pdf(path: str | Path) -> dict[str, int]:
    target = Path(path)
    data = target.read_bytes()
    counts: dict[str, int] = {}

    data, counts["info_dates"] = re.subn(
        rb"D:\d{14}[+-]\d{2}'\d{2}'",
        b"D:20000101000000+00'00'",
        data,
    )

    def _iso(match: re.Match[bytes]) -> bytes:
        return b"2000-01-01T00:00:00" + (b"Z" if match.group(0).endswith(b"Z") else b"")

    data, counts["xmp_dates"] = re.subn(
        rb"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z?", _iso, data
    )

    def _uuid(match: re.Match[bytes]) -> bytes:
        return match.group(1) + _ZERO_UUID + match.group(2)

    data, counts["xmp_uuids"] = re.subn(
        rb"(<xmpMM:(?:DocumentID|InstanceID)>uuid:)[0-9A-Fa-f-]{36}(</xmpMM:(?:DocumentID|InstanceID)>)",
        _uuid,
        data,
    )
    data, counts["trailer_ids"] = re.subn(
        rb"/ID\s*\[<[0-9A-Fa-f]{32}><[0-9A-Fa-f]{32}>\]",
        b"/ID[<00000000000000000000000000000000><00000000000000000000000000000000>]",
        data,
    )
    if not sum(counts.values()):
        raise RuntimeError(f"no volatile PDF metadata found in {target}")
    target.write_bytes(data)
    return counts


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: normalize_pdf_metadata.py PDF [PDF ...]", file=sys.stderr)
        return 2
    for name in argv[1:]:
        counts = normalize_pdf(name)
        print(f"normalized PDF metadata: {name} {counts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
