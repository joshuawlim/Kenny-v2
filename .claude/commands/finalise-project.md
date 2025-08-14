description: Complete all tasks and commit changes with detailed message

1. Open tasks.md.
2. Run "git status --porcelain" to list changed, added, or deleted files.
3. For each change not represented in tasks.md, append a new task and mark it "[X]".
4. Replace every remaining "[ ]" with "[X]".
5. Save tasks.md.
6. Generate a commit message summarising actual changes:
   • list each modified file with a short description
   • group related files together
7. Execute:
   git add .
   git commit -m "<generated message>"
8. Report that all tasks (including newly added ones) are complete and the commit with an itemised summary has been created.