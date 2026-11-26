#!/usr/bin/env bash
# Install Titan Enquiry Desk on an existing bench site (Mac/Linux).
# Usage: scripts/init.sh <bench-path> <site> [git-ref]
# Never run against production without a backup and client approval.
set -euo pipefail
BENCH=${1:?bench path}; SITE=${2:?site name}; REF=${3:-main}
REPO=https://github.com/supagigs/TitanEnquiryDesk.git
cd "$BENCH"
[ -d "sites/$SITE" ] || { echo "Site $SITE not found in $BENCH"; exit 1; }
for app in crm frappe_whatsapp; do
  bench --site "$SITE" list-apps | grep -q "^$app" || echo "WARNING: $app is not installed on $SITE (the desk needs crm; WhatsApp features need frappe_whatsapp)"
done
echo "Backing up $SITE..."; bench --site "$SITE" backup --with-files
if [ -d apps/titan_desk ]; then echo "apps/titan_desk already exists; use scripts/update.sh instead"; exit 1; fi
bench get-app titan_desk "$REPO" --branch "$REF"
bench --site "$SITE" install-app titan_desk
bench build --app titan_desk
bench --site "$SITE" clear-cache
curl -fsS -o /dev/null "$(bench --site "$SITE" execute frappe.utils.get_url 2>/dev/null | tr -d '"')/api/method/ping" && echo "Health check OK" || echo "Health check could not reach the site URL; check manually"
echo "Done. Open /titan-desk and give users the Titan Sales User / Titan Sales Manager / Titan Desk Admin roles."
