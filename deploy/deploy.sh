#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Deploy website-grader to a DigitalOcean Droplet
#
# Usage:
#   ./deploy.sh                          # deploy with defaults
#   ./deploy.sh --domain grader.example.com   # with custom domain
#   ./deploy.sh --help                   # full options
#
# Prerequisites (one-time):
#   1. Create a droplet (Ubuntu 24.04, $6/mo or higher)
#   2. Point your domain's A record to the droplet IP
#   3. Install Docker + docker-compose-plugin on the droplet:
#        curl -fsSL https://get.docker.com | sh
#   4. Set these env vars or pass via flags:
#        export DROPLET_IP="your.droplet.ip"
#        export DROPLET_USER="root"
#        export RESEND_API_KEY="re_..."
#        export RESEND_AUDIENCE_ID="your_audience_id"
# =============================================================================
set -euo pipefail

# ─── Config ──────────────────────────────────────────────────────────────────
DROPLET_IP="${DROPLET_IP:-}"
DROPLET_USER="${DROPLET_USER:-root}"
DOMAIN=""
SSH_KEY="${SSH_KEY:-}"
RESEND_API_KEY="${RESEND_API_KEY:-}"
RESEND_AUDIENCE_ID="${RESEND_AUDIENCE_ID:-}"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# ─── Parse flags ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case "$1" in
        --domain) DOMAIN="$2"; shift 2 ;;
        --ip) DROPLET_IP="$2"; shift 2 ;;
        --user) DROPLET_USER="$2"; shift 2 ;;
        --ssh-key) SSH_KEY="$2"; shift 2 ;;
        --resend-api-key) RESEND_API_KEY="$2"; shift 2 ;;
        --resend-audience-id) RESEND_AUDIENCE_ID="$2"; shift 2 ;;
        --help|-h)
            echo "Usage: $0 [options]"
            echo "  --domain <domain>       Domain name (e.g. grader.example.com)"
            echo "  --ip <ip>               Droplet IP address"
            echo "  --user <user>           SSH user (default: root)"
            echo "  --ssh-key <path>        SSH private key path"
            echo "  --resend-api-key <key>  Resend API key"
            echo "  --resend-audience-id <id>  Resend audience ID"
            exit 0 ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# ─── Validate ────────────────────────────────────────────────────────────────
if [[ -z "$DROPLET_IP" ]]; then
    echo "ERROR: DROPLET_IP not set. Use --ip or export DROPLET_IP=..."
    exit 1
fi

SSH_OPTS="-o StrictHostKeyChecking=accept-new"
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

echo "🚀 Deploying website-grader to $DROPLET_USER@$DROPLET_IP"

# ─── 1. Ensure Docker is installed on the droplet ────────────────────────────
echo "📦 Checking Docker on droplet..."
ssh $SSH_OPTS "$DROPLET_USER@$DROPLET_IP" "command -v docker &>/dev/null || (curl -fsSL https://get.docker.com | sh)" &
wait

# ─── 2. Copy project to droplet ─────────────────────────────────────────────
echo "📁 Copying project files..."
rsync -avz --delete \
    -e "ssh $SSH_OPTS" \
    --exclude '.git' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.pytest_cache' \
    --exclude '.env' \
    "$REPO_DIR/" \
    "$DROPLET_USER@$DROPLET_IP:/opt/website-grader/"

# ─── 3. Create .env on droplet ───────────────────────────────────────────────
echo "🔐 Writing .env..."
ssh $SSH_OPTS "$DROPLET_USER@$DROPLET_IP" "cat > /opt/website-grader/.env << 'ENVEOF'
FLASK_ENV=production
PORT=5000
RESEND_API_KEY=$RESEND_API_KEY
RESEND_AUDIENCE_ID=$RESEND_AUDIENCE_ID
ENVEOF"

# ─── 4. Build and start ──────────────────────────────────────────────────────
echo "🐳 Building and starting containers..."
ssh $SSH_OPTS "$DROPLET_USER@$DROPLET_IP" "cd /opt/website-grader && docker compose up --build -d"

# ─── 5. Health check ─────────────────────────────────────────────────────────
echo "⏳ Waiting for app to be healthy..."
for i in $(seq 1 12); do
    sleep 5
    if curl -sf "http://$DROPLET_IP/health" > /dev/null 2>&1; then
        echo "✅ App is healthy!"
        break
    fi
    if [[ $i -eq 12 ]]; then
        echo "❌ Health check failed after 60s. Check logs: docker compose logs app"
        exit 1
    fi
done

# ─── 6. Domain setup (optional) ──────────────────────────────────────────────
if [[ -n "$DOMAIN" ]]; then
    echo "🌐 Setting up domain: $DOMAIN"
    ssh $SSH_OPTS "$DROPLET_USER@$DROPLET_IP" "cat > /opt/website-grader/deploy/nginx.conf << 'NGINXEOF'
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        access_log off;
    }
}
NGINXEOF"
    ssh $SSH_OPTS "$DROPLET_USER@$DROPLET_IP" "cd /opt/website-grader && docker compose up --build -d"

    echo ""
    echo "============================================"
    echo "✅ Deployed!"
    echo "   http://$DOMAIN"
    echo "   Health: http://$DOMAIN/health"
    echo ""
    echo "📌 Next: Set up SSL with Certbot:"
    echo "   ssh $DROPLET_USER@$DROPLET_IP"
    echo "   apt install -y certbot python3-certbot-nginx"
    echo "   certbot --nginx -d $DOMAIN"
    echo "============================================"
else
    echo ""
    echo "============================================"
    echo "✅ Deployed!"
    echo "   http://$DROPLET_IP"
    echo "   Health: http://$DROPLET_IP/health"
    echo ""
    echo "📌 Next: Point a domain → $DROPLET_IP, then:"
    echo "   ./deploy.sh --domain grader.example.com --ip $DROPLET_IP"
    echo "============================================"
fi
