# Project workflow

## Pull requests

The project owner requests a pull request to the original repository after every
completed major change.

- Work on a dedicated topic branch for each coherent feature, experiment milestone,
  or substantial documentation change.
- Run the checks appropriate to that change and update the implementation/progress
  documentation. Explain new architectural choices in `doc/architecture.md`.
- Commit and push the topic branch, then open a pull request against
  `moneytosms/qcproj` (currently the default branch is `main`).
- Include the concrete change, verification evidence, and remaining research limits
  in the PR description. Return the PR link in the chat.
- Keep completed work reviewable through PRs; leave merging to the project owner.

For Python changes, run `uv run ruff check .`, `uv run ruff format --check .`, and
`uv run pytest -q`. Keep source PDFs unchanged. Do not commit downloaded datasets,
virtual environments, or generated experiment output. Smoke results must remain
clearly distinguished from completed scientific experiments.
