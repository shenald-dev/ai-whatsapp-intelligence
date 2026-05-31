with open("CHANGELOG.md.master", "r") as f:
    master_content = f.read()

new_content = """# Changelog

All notable changes to this project will be documented in this file.

## [1.0.28] - 2026-05-27

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations. Re-verified robust backend and node tests properly pass after migrating to a direct SQL `UPDATE` statement in the `process_message` Celery task.
* **Upgrades:** Checked minor/patch bumps for dependencies. Checked dependencies safely. Bumped project versions to `1.0.28`.
* **Pruning:** Checked unused imports and cleaned `__pycache__` artifacts to reduce codebase entropy.

## [1.0.27] - 2026-05-26

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing security bumps in the Node.js collector. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Audited dependencies and safely bumped 8 Python dependencies (`idna`, `click`, `wrapt`, `httptools`, `huggingface-hub`, `sqlalchemy`, `kubernetes`, `posthog`) via Poetry. Verified Node.js dependencies are up to date.
* **Pruning:** Pruned `__pycache__` artifacts to maintain codebase entropy.

## [1.0.27] - 2026-05-25

### Assure, Prune, and Sync
* **Lifecycle:** Verified system integrity post-optimizations introducing `ws` upgrade. Re-verified robust backend and node tests properly pass.
* **Upgrades:** Audited dependencies and safely bumped `python` dependencies via Poetry and Node.js dependencies via npm.
* **Pruning:** Pruned an unused import in test_workers.py.

"""

idx = master_content.find("## [1.0.26]")
if idx != -1:
    final_content = new_content + master_content[idx:]
else:
    final_content = new_content + master_content

with open("CHANGELOG.md", "w") as f:
    f.write(final_content)
