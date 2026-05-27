import sys

with open("CHANGELOG.md", "r") as f:
    content = f.read()

# Replace everything before "# Changelog" with just "# Changelog"
if "# Changelog\n" in content:
    idx = content.find("# Changelog\n")
    content = content[idx:]

with open("CHANGELOG.md", "w") as f:
    f.write(content)
