# Deployment guide

This repo contains:
- A Next.js frontend in `frontend/` (best on Vercel).
- A FastAPI backend in `backend/` (suitable for Render, Fly, or Cloud Run).

Recommended approaches:
- Frontend: connect `frontend/` to Vercel via GitHub integration (automatic on push), or use the included GitHub Actions workflow (`.github/workflows/deploy-frontend-vercel.yml`) which calls Vercel's CLI.
- Backend: build and push a Docker image, then deploy to Render (example workflow: `.github/workflows/deploy-backend-render.yml`). Alternatively deploy to Cloud Run or Fly with the Dockerfile.

Secrets required (set in GitHub repo Settings → Secrets):
- `VERCEL_TOKEN`, `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`
- `RENDER_API_KEY`, `RENDER_SERVICE_ID`
- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` (or use GitHub Packages)

Can we deploy directly via MCP?
- There is no built-in MCP action to deploy to Vercel or Render from here. Use GitHub Actions to call the platform CLIs/APIs, or push the repo and use Vercel/Render's GitHub integration.
- MCP *can* deploy Supabase Edge Functions via `mcp_supabase_deploy_edge_function` when using Supabase.

No-Docker (push & deploy)
-------------------------

If you don't have Docker locally, you can still push and deploy — platforms will build from source remotely.

- Frontend (Vercel):
	- Connect the GitHub repo to Vercel and set the project root to `MP_battle_of_build/memory-vault-mono/frontend`.
	- Vercel detects Next.js automatically and runs the build; no Docker needed locally.

- Backend (Render — remote build):
	- In Render, create a new **Web Service** and connect the GitHub repo.
	- Set the **Root Directory** to `MP_battle_of_build/memory-vault-mono/backend` so Render runs commands from the backend folder.
	- Build Command: `pip install -r requirements.txt`
	- Start Command: `uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers`
	- Add environment variables and secrets in Render's dashboard (e.g. `SUPABASE_URL`, `SUPABASE_KEY`, `REDIS_URL`).

- GitHub Actions (no Docker in CI):
	- The workflow `.github/workflows/deploy-backend-render.yml` now installs dependencies, runs backend tests (if present), and calls Render's API to trigger a remote build/deploy. The CI runner does not build or push Docker images.

Quick push & deploy (no Docker locally):

```bash
git checkout -b deploy/no-docker
git add .
git commit -m "Prepare remote build deployment (Render/Vercel)"
git push origin deploy/no-docker
# Open a PR and merge to main — workflows will trigger on push to main
```

Next steps I can take for you:
- Set up Render and Vercel projects (I can prepare exact UI values to paste).
- Add a small `check-secrets` workflow to validate required GitHub secrets.
- Open a PR with these changes and request a review.

Next steps I can take for you:
- Create the GitHub Actions workflows (done).
- Add a Docker Hub/GitHub Packages push configuration (done).
- Optionally wire up a GitHub Actions secret-check workflow and test-run the build locally.

If you want, I can also:
- Add a `docker-compose.yml` for local dev.
- Create a GitHub Action to run unit tests before deploy.
