# Website Grader — Droplet Deployment

## One-time droplet setup

```bash
# 1. Create a DigitalOcean Ubuntu 24.04 droplet ($6/mo or higher)
# 2. SSH in and install Docker:
curl -fsSL https://get.docker.com | sh
# 3. Log out, then deploy from your local machine
```

## Deploy

```bash
# From your local machine (this repo root):
export DROPLET_IP="your.droplet.ip"
export RESEND_API_KEY="re_..."
export RESEND_AUDIENCE_ID="your_audience_id"

./deploy/deploy.sh --domain grader.yourdomain.com
```

The script:
1. Copies the project to `/opt/website-grader/` on the droplet
2. Writes `.env` with your Resend credentials
3. Builds and starts the Docker container (nginx → gunicorn → Flask)
4. Runs a health check
5. Configures nginx for your domain

## SSL (after deploy)

```bash
ssh root@your.droplet.ip
apt install -y certbot python3-certbot-nginx
certbot --nginx -d grader.yourdomain.com
```

## Managing the app

```bash
ssh root@your.droplet.ip

# Logs
docker compose -f /opt/website-grader/docker-compose.yml logs -f app

# Restart
docker compose -f /opt/website-grader/docker-compose.yml restart app

# Update (pull new code and redeploy)
# From local: ./deploy/deploy.sh
