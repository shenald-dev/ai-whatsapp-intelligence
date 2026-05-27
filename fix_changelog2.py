import sys

with open("CHANGELOG.md", "r") as f:
    content = f.read()

content = content.replace("""## [1.0.27] - 2026-05-24

* **Maintenance**: Assure lifecycle, prune entropy.
* **Dependencies**: Safely bumped python and node dependencies.
* **Performance**: Checked for regressions.

""", "")

with open("CHANGELOG.md", "w") as f:
    f.write(content)
