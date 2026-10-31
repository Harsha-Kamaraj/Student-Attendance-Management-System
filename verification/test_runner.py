"""Opt-in JSON evidence for the existing Django test runner.

VERIFICATION_RESULTS=artifacts/tests.json python manage.py test \
    --testrunner verification.test_runner.Runner
"""

import json
import os
import time
import unittest
from datetime import UTC, datetime
from pathlib import Path

from django.conf import settings

from config.test_runner import Runner as ApplicationRunner


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.observations = []

    def startTest(self, test):
        self.started = time.perf_counter()
        self.current = {"test": test.id(), "status": "passed"}
        super().startTest(test)

    def addFailure(self, test, err):
        self.current["status"] = "failed"
        super().addFailure(test, err)

    def addError(self, test, err):
        self.current["status"] = "error"
        super().addError(test, err)

    def addSkip(self, test, reason):
        self.current.update(status="skipped", reason=reason)
        super().addSkip(test, reason)

    def addExpectedFailure(self, test, err):
        self.current["status"] = "expected_failure"
        super().addExpectedFailure(test, err)

    def addUnexpectedSuccess(self, test):
        self.current["status"] = "unexpected_success"
        super().addUnexpectedSuccess(test)

    def addSubTest(self, test, subtest, err):
        if err is not None:
            self.current["status"] = "failed"
        super().addSubTest(test, subtest, err)

    def stopTest(self, test):
        self.current["seconds"] = round(time.perf_counter() - self.started, 6)
        self.observations.append(self.current)
        super().stopTest(test)


class Runner(ApplicationRunner):
    def get_resultclass(self):
        return EvidenceResult

    def run_suite(self, suite, **kwargs):
        started = datetime.now(UTC)
        result = super().run_suite(suite, **kwargs)
        output = Path(os.environ.get("VERIFICATION_RESULTS", "artifacts/tests.json"))
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(
                {
                    "started_at": started.isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "tests_run": result.testsRun,
                    "successful": result.wasSuccessful(),
                    "failures": len(result.failures),
                    "errors": len(result.errors),
                    "skipped": len(result.skipped),
                    "password_hashers": list(settings.PASSWORD_HASHERS),
                    "results": result.observations,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        return result
