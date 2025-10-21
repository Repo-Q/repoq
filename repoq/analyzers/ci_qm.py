from __future__ import annotations

import glob
import os
import xml.etree.ElementTree as ET

from ..core.model import Project, TestCase, TestResult
from .base import Analyzer

JUNIT_GLOBS = [
    "target/surefire-reports/*.xml",
    "build/test-results/test/*.xml",
    "reports/tests/*.xml",
    "**/junit*.xml",
    "**/TEST-*.xml",
]


class CIQualityAnalyzer(Analyzer):
    name = "ci_qm"

    def run(self, project: Project, repo_dir: str, cfg) -> None:
        # search junit xmls
        for pattern in JUNIT_GLOBS:
            for path in glob.glob(os.path.join(repo_dir, pattern), recursive=True):
                try:
                    tree = ET.parse(path)  # nosec B314
                    root = tree.getroot()
                except Exception:
                    continue
                for tcase in root.iter("testcase"):
                    name = tcase.get("name") or "test"
                    classname = tcase.get("classname")
                    tc_id = (
                        f"repo:testcase:{classname}.{name}"
                        if classname
                        else f"repo:testcase:{name}"
                    )
                    if tc_id not in project.tests_cases:
                        project.tests_cases[tc_id] = TestCase(
                            id=tc_id, name=name, classname=classname
                        )

                    status = "passed"
                    message = None
                    time_val = None
                    if tcase.get("time"):
                        try:
                            time_val = float(tcase.get("time"))
                        except Exception:
                            time_val = None
                    # check for failure/error/skipped nodes
                    if tcase.find("failure") is not None:
                        status = "failed"
                        message = tcase.find("failure").get("message") or "failure"
                    elif tcase.find("error") is not None:
                        status = "error"
                        message = tcase.find("error").get("message") or "error"
                    elif tcase.find("skipped") is not None:
                        status = "skipped"

                    tr_id = f"{tc_id}#result-{abs(hash((tc_id,status,message,time_val)))%100000}"
                    project.tests_results.append(
                        TestResult(
                            id=tr_id,
                            testcase=tc_id,
                            status=status,
                            time=time_val,
                            message=message,
                        )
                    )
