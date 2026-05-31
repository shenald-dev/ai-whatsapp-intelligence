with open("backend/poetry.lock", "r") as f:
    l = f.read()

import re

l = re.sub(r'<<<<<<< HEAD.*?=======\nversion = "7\.15\.4"\n>>>>>>> origin/master', 'version = "7.15.4"', l, flags=re.DOTALL)
l = re.sub(r'<<<<<<< HEAD.*?=======\n    \{file = "posthog-7\.15\.4-py3-none-any\.whl".*?\n    \{file = "posthog-7\.15\.4\.tar\.gz".*?\n>>>>>>> origin/master', '    {file = "posthog-7.15.4-py3-none-any.whl", hash = "sha256:96f3a530a0dd709b91322212c61e161bf1e17a88d5202206870381222bc0fe2d"},\n    {file = "posthog-7.15.4.tar.gz", hash = "sha256:9d7fe7bc0f03ed699e0608be0a6ef60267129a597651eb1c78c89c290c0a9b18"},', l, flags=re.DOTALL)


with open("backend/poetry.lock", "w") as f:
    f.write(l)
