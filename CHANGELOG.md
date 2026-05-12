We are given a 3-way merge scenario for the file `CHANGELOG.md`.
 We have:
   - Ancestor: the common base
   - Base (master): the target branch (has newer changes from others)
   - Head (jules-...): the PR branch (has the PR author's changes)

 The goal is to resolve the conflict by keeping all meaningful changes from both branches.

 Steps:
 1. We

// ... 26038 characters truncated (middle section) ...

umber but different dates.

        4. Actually, looking at the diff:
            Base (master) had:
                ## [1.0.24] - 2026-05-05
                ... (some changes)

        5. ... and so on.

     This is not changelog content.

 51. The only actual changelog changes in the Head branch's addition are:

        -## [1.0.23] - 2026-05-05