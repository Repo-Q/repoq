"""Debug stakeholder parsing."""

import re
from textwrap import dedent

content = dedent("""\
    # Phase 2: Value Register

    ## V01: Transparency

    The system must provide clear visibility into code quality metrics.

    **Tier**: 1
    **Priority**: P0
    **Stakeholders**: Alex, Morgan

    Satisfied by: FR-01, FR-05

    ## Stakeholder Profiles

    ### Alex (Senior Developer)

    **Interests**:
    - Code quality metrics
    - Automated analysis

    **Concerns**:
    - Performance overhead
    - False positives

    ### Morgan (Team Lead)

    **Interests**:
    - Team productivity
    - Technical debt tracking

    **Concerns**:
    - Integration complexity

    ### Casey (DevOps Engineer)

    **Interests**:
    - CI/CD integration
    - Reproducibility

    **Concerns**:
    - Build time impact
""")

# Test 1: Find section
stakeholder_section = re.search(r"##\s+Stakeholder Profiles(.+?)(?=\n##|$)", content, re.DOTALL)
if stakeholder_section:
    print("✓ Found Stakeholder Profiles section")
    text = stakeholder_section.group(1)
    print(f"  Length: {len(text)} chars")

    # Test 2: Find stakeholders
    pattern = r"###\s+(.+?)\s*\((.+?)\)\s*\n(.+?)(?=\n###|$)"
    matches = list(re.finditer(pattern, text, re.DOTALL))
    print(f"✓ Found {len(matches)} stakeholders")

    for m in matches:
        name = m.group(1).strip()
        role = m.group(2).strip()
        body = m.group(3)
        print(f"  - {name} ({role})")

        # Test 3: Extract interests
        interests_match = re.search(r"\*\*Interests\*\*:(.+?)(?:\*\*|$)", body, re.DOTALL)
        if interests_match:
            interests = []
            for line in interests_match.group(1).strip().split("\n"):
                if line.strip().startswith("-"):
                    interests.append(line.strip()[1:].strip())
            print(f"    Interests: {len(interests)}")
            for i in interests:
                print(f"      • {i}")
else:
    print("✗ Stakeholder Profiles section NOT found")

    # Debug: show all ## headers
    headers = re.findall(r"##\s+(.+)", content)
    print(f"  Found headers: {headers}")
