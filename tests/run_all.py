""" Run all tests: python tests/run_all.py

Scenarios of all test files run through one shared pool of processes
(BATTLE_CITY_TEST_WORKERS environment variable, default os.cpu_count()).
Output of every file is printed as one block in file name order.
"""

import os, sys, glob, importlib.util

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, TESTS_DIR)

import harness


def load_scenarios(path):
	name = os.path.splitext(os.path.basename(path))[0]
	spec = importlib.util.spec_from_file_location(name, path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module.SCENARIOS


files = []
jobs = []
for path in sorted(glob.glob(os.path.join(TESTS_DIR, "test_*.py"))):
	scenarios = load_scenarios(path)
	files.append((os.path.basename(path), len(scenarios)))
	jobs += [(path, name, scenarios[name]) for name in scenarios]

failed_files = []
results = harness.run_parallel(jobs)
for name, count in files:
	block = ["== " + name]
	ok = True
	for _ in range(count):
		output, passed = next(results)
		if output:
			block.append(output)
		ok = ok and passed
	if not ok:
		failed_files.append(name)
	print("\n".join(block))
	sys.stdout.flush()

print("")
if failed_files:
	print("FAILED: " + ", ".join(failed_files))
	sys.exit(1)
print("ALL TESTS PASSED")
