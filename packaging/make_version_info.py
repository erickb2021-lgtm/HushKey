"""Writes packaging/version_info.txt, the "Details" tab Windows shows for HushKey.exe.

Antivirus programs are more suspicious of .exe files with no name, company,
or version, so we fill these in properly.

Usage:  python packaging/make_version_info.py 1.2.3
"""
import os
import sys

PUBLISHER = "Erick Bardales"

version = (sys.argv[1] if len(sys.argv) > 1 else "2.0.12").lstrip("vV")
parts = [int(p) if p.isdigit() else 0 for p in version.split(".")[:4]]
parts += [0] * (4 - len(parts))
ver_tuple = tuple(parts)
ver_str = ".".join(str(p) for p in parts)

template = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={ver_tuple}, prodvers={ver_tuple},
                    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{PUBLISHER}'),
      StringStruct('FileDescription', 'HushKey Password Manager'),
      StringStruct('FileVersion', '{ver_str}'),
      StringStruct('InternalName', 'HushKey'),
      StringStruct('LegalCopyright', 'Copyright (c) 2026 {PUBLISHER}'),
      StringStruct('OriginalFilename', 'HushKey.exe'),
      StringStruct('ProductName', 'HushKey'),
      StringStruct('ProductVersion', '{ver_str}')])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""
out = os.path.join(os.path.dirname(__file__), "version_info.txt")
with open(out, "w", encoding="utf-8") as f:
    f.write(template)
print("wrote", out, "for version", ver_str)
