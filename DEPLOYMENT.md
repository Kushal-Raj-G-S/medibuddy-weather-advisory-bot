# Deployment

Two pieces, two hosts, because the backend needs to run Python (LangGraph,
the NVIDIA client, the SOP loader) and hold the API key server-side — it
cannot be static hosting. The frontend is a static/edge-renderable Next.js
app, so it goes somewhere built for that.

- **Backend** (FastAPI + LangGraph): **Render** (free tier)
- **Frontend** (Next.js): **Vercel** (free tier)

Both support one-click GitHub-connected deploys. Total time: ~10 minutes.

## 1. Deploy the backend on Render

1. Go to [render.com](https://render.com), sign up / log in with GitHub.
2. **New → Blueprint**, pick this repo
   (`Kushal-Raj-G-S/medibuddy-weather-advisory-bot`). Render reads
   `render.yaml` at the repo root automatically and pre-fills everything
   except two secrets.
3. When prompted, paste in:
   - `NVIDIA_API_KEY` — your NVIDIA build.nvidia.com key
   - `CORS_ALLOW_ORIGINS` — leave blank for now, come back after step 2
4. Deploy. Render gives you a URL like
   `https://weather-advisory-bot-api.onrender.com`. **Copy it.**
5. Confirm it's alive: `https://<that-url>/api/health` should return
   `{"ok":true}`, and `/api/policy` should return the 14 SOPs.

**Free-tier note:** Render's free web services spin down after ~15 minutes
of no traffic and take 30–60s to wake back up on the next request. If the
reviewer's first request seems to hang, that's why — not a bug. Worth
mentioning in the form's "anything we should know" field.

## 2. Deploy the frontend on Vercel

1. Go to [vercel.com](https://vercel.com), sign up / log in with GitHub.
2. **Add New → Project**, import the same repo.
3. Under **Root Directory**, click Edit and select `web` — this is a
   monorepo (the Next.js app isn't at the repo root), so this step is not
   optional.
4. Framework preset should auto-detect as Next.js. Leave build/output
   settings as default.
5. Under **Environment Variables**, add:
   - `NEXT_PUBLIC_API_URL` = the Render URL from step 1 (no trailing slash)
6. Deploy. Vercel gives you a URL like
   `https://medibuddy-weather-advisory-bot.vercel.app`. **This is the "Live
   app URL" for the submission form.**

## 3. Close the loop: tell the backend about the frontend's real origin

Go back to the Render dashboard → your service → **Environment**, set:

- `CORS_ALLOW_ORIGINS` = the exact Vercel URL from step 2 (e.g.
  `https://medibuddy-weather-advisory-bot.vercel.app`) — no trailing slash,
  no wildcard. `api/main.py` reads this as an exact-match allowlist on top
  of the localhost regex it already allows for local dev.

Save — Render redeploys automatically. Without this step the deployed
frontend's requests to `/api/ask` will be blocked by CORS in the browser
(they'll work fine when you test locally, which is precisely why this is
easy to miss until a reviewer opens the real URL).

## 4. Verify the real thing, not just that it loaded

Open the Vercel URL and actually ask it something — a page that loads isn't
proof the backend is reachable. A good check: ask a real question (e.g.
"is it safe to cycle in Bhopal today?") and confirm a citation appears
under the reply, not just that the input box is present.

## What NOT to deploy

The Streamlit frontend (`frontend/streamlit_app.py`) is documented as a
local fallback and isn't part of this deployment — it imports `app/graph.py`
directly in-process rather than calling an API, so "deploying" it would mean
a third hosted service for no benefit over what Vercel + Render already
cover. If a reviewer specifically wants to see it, `streamlit run
frontend/streamlit_app.py` still works locally exactly as before.
