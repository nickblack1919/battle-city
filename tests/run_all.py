""" Run all tests: python tests/run_all.py """

import os, sys, glob, subprocess

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

failed_files = []
for path in sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py"))):
	name = os.path.basename(path)
	print("== " + name)
	sys.stdout.flush()
	if subprocess.call([sys.executable, path]) != 0:
		failed_files.append(name)

print("")
if failed_files:
	print("FAILED: " + ", ".join(failed_files))
	sys.exit(1)
print("ALL TESTS PASSED")
