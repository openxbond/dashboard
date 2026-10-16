"""Validate and package the deliberately small public distribution surface."""

import argparse
import hashlib
from pathlib import Path, PurePosixPath
import re
import stat
import zipfile

TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-([0-9A-Za-z.-]+))?(?:\+[0-9A-Za-z.-]+)?\Z")
EXTENSIONS = {".js", ".css", ".svg", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".avif", ".ico", ".woff", ".woff2", ".ttf", ".eot"}
ROOT_FILES = {"index.html", "manifest.webmanifest", ".nojekyll", "LICENSE", "THIRD_PARTY_NOTICES.txt"}
SOURCE_MAP = re.compile(rb"(?://[#@]|/\*[#@])\s*sourceMappingURL\s*=")
SECRET = re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----|\b(?:ghp_|github_pat_|ghs_)[A-Za-z0-9_]{20,}")
MAX_SIZE = 200 * 1024 * 1024


def validate_tag(tag):
    match = TAG.fullmatch(tag)
    if not match:
        raise ValueError("Expected a version tag such as v0.4.0")
    return tuple(int(match[i]) for i in (1, 2, 3)), match[4]


def checksum(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_archive(archive, checksums=None, extract=None):
    archive = Path(archive)
    digest = checksum(archive)
    if checksums and Path(checksums).read_text(encoding="utf-8") != f"{digest}  dashboard.zip\n":
        raise ValueError("SHA256SUMS does not match dashboard.zip")
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        if len(entries) > 10000 or sum(e.file_size for e in entries) > MAX_SIZE:
            raise ValueError("Archive exceeds distribution limits")
        seen = set()
        for entry in entries:
            name = entry.orig_filename
            path = PurePosixPath(name)
            if (not name or "\\" in name or path.is_absolute() or ":" in name
                    or any(ord(char) < 32 for char in name)
                    or path.as_posix() != name.rstrip("/")
                    or any(part in {"..", "."} for part in name.rstrip("/").split("/"))
                    or any(part.startswith(".") for part in path.parts if part != ".nojekyll")):
                raise ValueError(f"Unsafe archive path: {name}")
            if name.casefold() in seen:
                raise ValueError(f"Duplicate archive path: {name}")
            seen.add(name.casefold())
            mode = entry.external_attr >> 16
            if stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in {0, stat.S_IFREG, stat.S_IFDIR}):
                raise ValueError(f"Unsupported archive entry: {name}")
            if entry.is_dir():
                continue
            allowed = name in ROOT_FILES or (path.suffix.lower() in EXTENSIONS and
                      (len(path.parts) == 1 or path.parts[0] in {"assets", "icons"}))
            if not allowed:
                raise ValueError(f"Not a compiled distribution file: {name}")
            data = package.read(entry)
            if SECRET.search(data) or (path.suffix.lower() in {".js", ".css"} and SOURCE_MAP.search(data)):
                raise ValueError(f"Secret or source map reference in: {name}")
        if "index.html" not in package.namelist():
            raise ValueError("index.html must be at the archive root")
        # Extract only after every entry has passed validation.
        if extract:
            package.extractall(extract)
    return digest


def package_distribution(directory, output):
    directory, output = Path(directory), Path(output)
    output.mkdir(parents=True, exist_ok=True)
    archive = output / "dashboard.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as package:
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink in distribution: {path}")
            if path.is_file():
                entry = zipfile.ZipInfo(path.relative_to(directory).as_posix())
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = (stat.S_IFREG | 0o644) << 16
                package.writestr(entry, path.read_bytes())
    digest = validate_archive(archive)
    (output / "SHA256SUMS").write_text(f"{digest}  dashboard.zip\n", encoding="utf-8", newline="\n")
    return digest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    package = commands.add_parser("package")
    package.add_argument("directory")
    package.add_argument("output")
    validate = commands.add_parser("validate")
    validate.add_argument("archive")
    validate.add_argument("checksums")
    validate.add_argument("--extract")
    args = parser.parse_args()
    if args.command == "package":
        print(package_distribution(args.directory, args.output))
    else:
        print(validate_archive(args.archive, args.checksums, args.extract))
