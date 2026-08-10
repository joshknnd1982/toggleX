#!/usr/bin/env python3
"""Packages addon/ into a .nvda-addon bundle.

An NVDA add-on is a zip archive with manifest.ini at its root. Stdlib only, so
this runs anywhere Python 3 does.
"""

import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.abspath(__file__))
ADDON_DIR = os.path.join(ROOT, "addon")
EXCLUDED_DIRS = {"__pycache__", ".git"}
EXCLUDED_SUFFIXES = (".pyc", ".pyo")


def readManifestField(name):
	"""Reads a top level field out of the manifest without needing configobj."""
	path = os.path.join(ADDON_DIR, "manifest.ini")
	with open(path, encoding="utf-8") as f:
		for line in f:
			match = re.match(r"""^\s*%s\s*=\s*(.+?)\s*$""" % name, line)
			if match:
				return match.group(1).strip("\"'")
	raise SystemExit("%s is missing a %s field" % (path, name))


def collectFiles():
	for dirPath, dirNames, fileNames in os.walk(ADDON_DIR):
		dirNames[:] = sorted(d for d in dirNames if d not in EXCLUDED_DIRS)
		for fileName in sorted(fileNames):
			if fileName.endswith(EXCLUDED_SUFFIXES):
				continue
			absPath = os.path.join(dirPath, fileName)
			# Archive paths are relative to addon/, so manifest.ini lands at the root.
			yield absPath, os.path.relpath(absPath, ADDON_DIR).replace(os.sep, "/")


def main():
	if not os.path.isfile(os.path.join(ADDON_DIR, "manifest.ini")):
		raise SystemExit("no manifest.ini found in %s" % ADDON_DIR)
	name = readManifestField("name")
	version = readManifestField("version")
	docFileName = readManifestField("docFileName")

	files = list(collectFiles())
	archivePaths = {archivePath for _, archivePath in files}
	for required in ("manifest.ini", "globalPlugins/%s.py" % name, "doc/en/%s" % docFileName):
		if required not in archivePaths:
			raise SystemExit("expected %s in the bundle but it is missing" % required)

	target = os.path.join(ROOT, "%s-%s.nvda-addon" % (name, version))
	with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as bundle:
		for absPath, archivePath in files:
			bundle.write(absPath, archivePath)

	print("built %s" % os.path.basename(target))
	for archivePath in sorted(archivePaths):
		print("  %s" % archivePath)
	print("%d files, %d bytes" % (len(files), os.path.getsize(target)))


if __name__ == "__main__":
	sys.exit(main())
