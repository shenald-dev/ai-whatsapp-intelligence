import sys
import re

with open(".jules/warden.md", "r") as f:
    content = f.read()

# The file got completely messed up by multiple conflict markers and some weird explanatory text added during a previous failed conflict resolution.
# Let's just rewrite the entire .jules/warden.md based on origin/master, and then prepend our changes.
