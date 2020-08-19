# -*- mode: python -*-
# coding: utf-8

import io
import os
import os.path
import re
import sys

from PyInstaller.utils.hooks import copy_metadata


def get_version(init_file):
    """ Find the current version. """

    with io.open(init_file, encoding="utf-8") as handler:
        for line in handler.readlines():
            if line.startswith("__version__"):
                return re.findall(r"\"(.+)\"", line)[0]


icon = {
    "darwin": "app_icon.icns",
    "linux": "app_icon.png",
    "win32": "packaging\\windows\\pictures\\app_icon.ico",
}[sys.platform]

excludes = [
    # https://github.com/pyinstaller/pyinstaller/wiki/Recipe-remove-tkinter-tcl
    "FixTk",
    "tcl",
    "tk",
    "_tkinter",
    "tkinter",
    "Tkinter",
    # Misc
    "PIL",
    "ipdb",
    "lib2to3",
    "numpy",
    "pydev",
    "scipy",
    "yappi",
]

data = [("trafic.svg", ".")]
data.extend(copy_metadata("tendo"))  # See issue BoboTiG/watermark-me#75
version = get_version("trafic/__init__.py")
properties_rc = None

if sys.platform == "win32":
    # Set executable properties
    properties_tpl = "installer\\windows\\properties_tpl.rc"
    properties_rc = "installer\\windows\\properties.rc"
    if os.path.isfile(properties_rc):
        os.remove(properties_rc)

    version_tuple = tuple(map(int, version.split(".") + [0] * (3 - version.count("."))))

    with open(properties_tpl) as tpl, open(properties_rc, "w") as out:
        content = tpl.read().format(version=version, version_tuple=version_tuple)
        print(content)
        out.write(content)

a = Analysis(
    ["trafic/__main__.py"],
    datas=data,
    excludes=excludes,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="trafic",
    console=False,
    debug=False,
    strip=False,
    upx=False,
    icon=icon,
    version=properties_rc,
)

coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, name="trafic")

info_plist = {
    "CFBundleName": "Trafic",
    "CFBundleShortVersionString": version,
    "LSUIElement": True,  # Implies LSBackgroundOnly, no icon in the Dock
    "NSHighResolutionCapable": True,
}

app = BUNDLE(
    coll,
    name="Trafic.app",
    icon=icon,
    info_plist=info_plist,
    bundle_identifier="org.trafic",
)
