---
description: Auto-commit all changes, push to a feature branch, and create a PR
---

# Commit & PR Workflow

Automatically commit all current changes, push to a new feature branch, and create a GitHub Pull Request. Run this whenever you need to save your work to GitHub.

## Steps

1. **Check for changes**: Run `git status` and `git diff --stat`. If there are no changes (working tree is clean), inform the user and stop.

2. **Analyze changes**: Look at the diff to understand what was changed. Determine a short, descriptive branch name (e.g., `feat/add-launch-json`, `fix/update-styles`, `chore/update-deps`).

3. **Create feature branch**: Run `git checkout -b <branch-name>` from the current branch.

4. **Stage all changes**: Run `git add` for all modified and untracked files. Use specific file paths — avoid `git add -A` or `git add .` to prevent accidentally staging sensitive files like `.env`.

5. **Commit**: Create a well-structured commit message following conventional commit style:
   - First line: concise summary (imperative mood, under 72 chars)
   - Blank line, then bullet points describing key changes
   - End with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
   - Use HEREDOC format for the message.

6. **Push**: Run `git push -u origin <branch-name>`.

7. **Create PR**: Use `gh pr create` (via full path `"/c/Program Files/GitHub CLI/gh.exe"` on Windows) with:
   - A concise title (under 70 chars)
   - A body with `## Summary` (bullet points) and `## Test plan` (checklist)
   - Use HEREDOC for the body.

8. **Report**: Show the user the PR URL and a summary of what was committed.

9. **Code Review**: After the PR is created, automatically run the `/code-review` skill on the newly created PR. This provides automated bug detection, CLAUDE.md compliance checking, and historical context analysis before the PR is merged.

## Important Notes
- Never force-push or amend previous commits
- Never commit `.env` files or secrets
- Always create a NEW branch — never commit directly to `master`/`main`
- If `gh` CLI is not found at the standard path, try `gh` directly
- After PR creation, switch back to the base branch with `git checkout master`
