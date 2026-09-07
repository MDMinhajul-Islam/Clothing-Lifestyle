"""Run historical local tests; never construct the live gateway integration suite.

All TestToolGatewayAPI methods are excluded: even reads persist audit records.
No changes to the historical tests or business rules are required.
"""
import json
import unittest
import tempfile
from .common import ROOT, write

def flatten(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from flatten(test)
        else:
            yield test

def main():
    temp_root = (ROOT / 'tmp/phase_2d_tests').resolve()
    assert temp_root.is_relative_to(ROOT.resolve())
    temp_root.mkdir(parents=True, exist_ok=True)
    tempfile.tempdir = str(temp_root)
    discovered = unittest.TestLoader().discover(str(ROOT/'tests'))
    selected, excluded = [], []
    for test in flatten(discovered):
        if '.TestToolGatewayAPI.' in test.id():
            excluded.append(test.id())
        else:
            selected.append(test)
    result = unittest.TextTestRunner(verbosity=1).run(unittest.TestSuite(selected))
    write(ROOT/'reports/phase_2d_safe_tests.json', dict(run=result.testsRun, failures=len(result.failures),
        errors=len(result.errors), skipped=len(result.skipped), excluded_live_gateway_tests=excluded,
        historical_baseline=83, success=result.wasSuccessful()))
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__ == '__main__':
    main()
