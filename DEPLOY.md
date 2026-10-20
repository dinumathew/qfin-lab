# Deploy QFin Lab on Streamlit Community Cloud (free)

1. Create a free GitHub account (github.com) and a **private** repository named `qfin-lab`.
2. Upload the project: in the empty repo click **uploading an existing file**, drag in the *contents* of the
   `qfin_lab` folder (app.py, requirements.txt, core/, app_pages/, content/, data/, tests/, .streamlit/ …),
   then **Commit changes**. Do not upload `.venv` or any `secrets.toml`.
   (Folders starting with a dot can be hidden in Explorer: View → Show → Hidden items.)
3. Go to share.streamlit.io, **Continue with GitHub**, and authorise access to the private repo.
4. **Create app → Deploy a public app from GitHub**: repository `<you>/qfin-lab`, branch `main`,
   main file `app.py`, choose a custom URL (e.g. `qfin-lab-dinu`).
5. **Advanced settings**: Python **3.12**; in **Secrets** paste:
   ```
   [auth]
   username = "dinu"
   password = "<your password>"
   # ANTHROPIC_API_KEY = "sk-ant-..."   (optional, enables the Claude tutor)
   ```
6. **Deploy**. First build takes ~5 minutes. Your URL: `https://<custom-name>.streamlit.app`.

## Important
* **Progress is not kept across restarts.** The cloud disk resets on reboot, redeploy or after the app sleeps
  (no visits for 12 hours). Use *Lab environment & settings → Download progress backup* after each session,
  and *Restore* after a restart.
* Change the password any time: app **⋮ → Settings → Secrets**, edit, Save (app restarts).
* Limits on the free tier: ~2.7 GB RAM, up to 2 CPU cores. All Level 0–1 labs fit.
* The app executes Python code you type. Keep the password private.
