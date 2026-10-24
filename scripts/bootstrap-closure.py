#!/usr/bin/env python3
"""Print the runtime dependency closure (Depends + Pre-Depends) of the given
root packages, using the .deb files found in a directory.

usage: bootstrap-closure.py DEBS_DIR ARCH ROOT_PACKAGE [ROOT_PACKAGE ...]
Warnings go to stderr, the package names (one per line) go to stdout.
"""
import glob
import os
import re
import subprocess
import sys


def read_fields(deb):
    out = subprocess.run(
        ["dpkg-deb", "-f", deb, "Package", "Architecture", "Depends", "Pre-Depends"],
        capture_output=True, text=True, check=True,
    ).stdout
    fields, key = {}, None
    for line in out.splitlines():
        if line[:1] in (" ", "\t") and key:
            fields[key] += " " + line.strip()
        elif ":" in line:
            key, value = line.split(":", 1)
            fields[key] = value.strip()
    return fields


def main():
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    debs_dir, arch, roots = sys.argv[1], sys.argv[2], sys.argv[3:]

    pkgs = {}
    for deb in sorted(glob.glob(os.path.join(debs_dir, "*.deb"))):
        f = read_fields(deb)
        name = f.get("Package")
        if not name or f.get("Architecture") not in (arch, "all") or name.endswith("-static"):
            continue
        groups = []
        for key in ("Depends", "Pre-Depends"):
            for group in f.get(key, "").split(","):
                alts = [re.split(r"[ (:]", a.strip())[0] for a in group.split("|") if a.strip()]
                if alts:
                    groups.append(alts)
        pkgs[name] = groups

    needed, queue = set(), list(roots)
    while queue:
        name = queue.pop()
        if name in needed:
            continue
        if name not in pkgs:
            print("WARNING: no deb found for '%s'" % name, file=sys.stderr)
            continue
        needed.add(name)
        for alts in pkgs[name]:
            pick = next((a for a in alts if a in pkgs), None)
            if pick is None:
                print("WARNING: '%s' depends on %s, none built" % (name, "|".join(alts)), file=sys.stderr)
            else:
                queue.append(pick)

    if not needed:
        sys.exit("ERROR: empty package closure")
    print("\n".join(sorted(needed)))


if __name__ == "__main__":
    main()
