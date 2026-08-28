# Deploying Viralist to Vercel

> 🌐 **Live Vercel Studio URL**: [https://frontend-psi-ruby-50.vercel.app](https://frontend-psi-ruby-50.vercel.app)

You can access the **Viralist AI Video Editor Studio** live on Vercel from any browser, tablet, or device.

---

## ⚡ Architecture: Global Vercel Frontend + Local/Cloud Engine

- **Frontend (Vercel)**: Hosted globally on Vercel's edge network as a high-performance React + TypeScript + Tailwind SPA.
- **Render Engine (Local / Cloud GPU)**: Runs locally on your machine (via `./scripts/start_editor.sh`) or on a cloud GPU instance (via Docker or Cloudflare Tunnel) to perform hardware-accelerated video rendering, Whisper transcription, Edge-TTS synthesis, and FFmpeg filtergraphs.

---

## 🚀 One-Click Deploy

1. **Deploy to Vercel**:
   - Push this repository to your GitHub account.
   - Import the repository in [Vercel](https://vercel.com/new).
   - Vercel will automatically detect `vercel.json` and build the frontend.

2. **Optional Environment Variables (in Vercel Project Settings)**:
   - `VITE_API_URL`: (Optional) The default URL of your backend engine (e.g. `https://my-editor-tunnel.trycloudflare.com` or `http://localhost:8080`).
   - `VITE_AUTH_TOKEN`: (Optional) The default Manager-signed auth token for protected environments.

---

## 💻 Connecting Your Local Machine to Vercel

Normal human users can connect their browser on Vercel to their local engine in 2 easy ways:

### Option A: Direct Localhost Connection (Same Machine)
1. Start your local Viralist engine in your terminal:
   ```bash
   ./scripts/start_editor.sh
   ```
2. Open your Vercel deployment URL (e.g. `https://my-viralist.vercel.app`).
3. Click the **Engine** pill in the top header (it will show **Demo Mode** or **Online**).
4. Select **Local Engine (`http://localhost:8080`)** and click **Save & Connect**.
5. The UI will instantly sync with your live timeline and local assets!

### Option B: Cloudflare Tunnel (Remote Access from Anywhere)
To access your home GPU workstation from anywhere in the world:
1. Start the Cloudflare quick tunnel:
   ```bash
   cloudflared tunnel --url http://localhost:8080
   ```
2. Copy the generated tunnel URL (e.g. `https://random-words.trycloudflare.com`).
3. Open your Vercel web app, click the **Engine** status pill, paste the tunnel URL, and click **Save & Connect**.
4. You can also click **Copy Share Link** in the modal to send a pre-connected link to collaborators (`https://my-app.vercel.app?backend=https://...`).

---

## 🧪 Built-in Interactive Demo Mode

If the backend is not running or unreachable, the Vercel web app automatically loads an interactive demo project (complete with 9:16 vertical video tracks, kinetic captions, color grading, and markers) so anyone can explore the NLE timeline, play with captions, and test the tools without having to configure a backend first.
