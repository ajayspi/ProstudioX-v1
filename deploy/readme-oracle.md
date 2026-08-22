# Deploy Prostudio v1 on Oracle Cloud (Always Free)

Runs the FastAPI backend (port 8000) and the Next.js frontend (port 3000) on a
single Always Free **A1.Flex (ARM)** instance under Ubuntu 22.04.

## 1. Create the instance (your OCI console)

- **Shape:** Ampere A1.Flex, **2 OCPU + 12 GB RAM** (Always Free; 4 OCPU/24 GB is
  also free if you want more headroom for ffmpeg).
- **Image:** Canonical Ubuntu 22.04 (aarch64).
- **SSH:** upload your public key.
- **Boot volume:** 100 GB (free tier includes 200 GB total).

## 2. Open ports (Security List / Network Security Group)

Add ingress rules (TCP) for:

| Port | Purpose |
|------|---------|
| 22   | SSH |
| 8000 | Backend (FastAPI) |
| 3000 | Frontend (Next.js) |

## 3. Deploy (one command)

SSH into the instance and run:

```bash
sudo bash -c "$(curl -fsSL https://raw.githubusercontent.com/ajayspi/Prostudio-v1/master/deploy/setup.sh)" -- <YOUR_PUBLIC_IP>
```

Or clone manually and run:

```bash
git clone https://github.com/ajayspi/Prostudio-v1.git
cd Prostudio-v1
sudo bash deploy/setup.sh <YOUR_PUBLIC_IP>
```

The script installs ffmpeg + Node 22 + Python, builds the frontend (baking in
`NEXT_PUBLIC_API_URL=http://<IP>:8000`), and installs two systemd services.

## 4. Use it

- **Frontend:** http://<YOUR_PUBLIC_IP>:3000
- **Backend health:** http://<YOUR_PUBLIC_IP>:8000/api/health

## 5. API keys

Two options:

- **Paste in the UI** — the frontend's "API keys" section sends keys with each
  generation (no server config needed). Fine for personal use.
- **Persist on the server** — create `/opt/prostudio-v1/backend/.env` with your
  keys (see `backend/.env.example`), then `sudo systemctl restart prostudio-v1-backend`.

## Managing the services

```bash
sudo systemctl status prostudio-v1-backend prostudio-v1-frontend
sudo journalctl -u prostudio-v1-backend -f      # live backend logs
sudo systemctl restart prostudio-v1-frontend
```

## Notes

- Keep `NEXT_PUBLIC_API_URL` in sync with your instance IP; if the IP changes
  (ephemeral), rebuild the frontend with the new IP and restart the service.
- For a hardened setup, put Nginx in front (single port 80/443, proxy `/api`
  and `/ws` to :8000 and serve the frontend) — this is optional for personal use.
