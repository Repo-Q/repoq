from __future__ import annotations
import os, glob, xml.etree.ElementTree as ET
from ..core.model import Project

class CIQualityAnalyzer:
    def run(self, p: Project, repo_dir: str, cfg):
        # CI presence
        if os.path.isdir(os.path.join(repo_dir, ".github","workflows")) or            os.path.isfile(os.path.join(repo_dir, ".travis.yml")) or            os.path.isfile(os.path.join(repo_dir, ".gitlab-ci.yml")):
            p.ci_configured = True
        # JUnit parse
        for pat in ("**/junit*.xml","**/TEST-*.xml"):
            for path in glob.glob(os.path.join(repo_dir, pat), recursive=True):
                try:
                    tree = ET.parse(path); root = tree.getroot()
                    if root.tag.endswith("testsuite"):
                        total = int(root.attrib.get("tests","0"))
                        failures = int(root.attrib.get("failures","0"))
                        errors = int(root.attrib.get("errors","0"))
                        p.tests_results.append({"suite": os.path.basename(path), "total": total, "failures": failures, "errors": errors})
                except Exception:
                    continue
