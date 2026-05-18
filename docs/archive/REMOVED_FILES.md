The following runtime and temporary files were removed from the repository to clean up the project root:

- `backend.log` — previously in the repo root; contains Uvicorn debug output and watch logs.
- `worker.log` — background AI worker logs.

These files are typically environment-specific and should not be committed. If you need to preserve their contents, retrieve them from the machine where they were generated before running the cleanup.

They have been removed and the repository updated to keep the code and docs tidy.
