#!/usr/bin/env bash

set -euo pipefail

SERVICE_USER="${SERVICE_USER:-callrating}"
SERVICE_GROUP="${SERVICE_GROUP:-${SERVICE_USER}}"
SERVICE_UID="${SERVICE_UID:-10001}"
BASE_DIR="${BASE_DIR:-/var/lib/call-rating}"
QUARANTINE_DIR="${QUARANTINE_DIR:-${BASE_DIR}/quarantine}"
ACCEPTED_DIR="${ACCEPTED_DIR:-${BASE_DIR}/accepted}"
REJECTED_DIR="${REJECTED_DIR:-${BASE_DIR}/rejected}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
LOG_DIR="${LOG_DIR:-/var/log/call-rating}"
SSH_ALLOWED_CIDR="${SSH_ALLOWED_CIDR:-}"
EGRESS_ALLOWED_CIDRS="${EGRESS_ALLOWED_CIDRS:-}"

log() {
  printf '[bootstrap] %s\n' "$*"
}

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Run this bootstrap script as root inside the guest VM." >&2
    exit 1
  fi
}

install_packages() {
  export DEBIAN_FRONTEND=noninteractive

  log "Updating package lists"
  apt-get update

  log "Installing baseline hardening packages"
  apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    openssh-server \
    sudo \
    ufw \
    unattended-upgrades

  log "Enabling unattended security updates"
  dpkg-reconfigure -f noninteractive unattended-upgrades || true

  cat >/etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
EOF
}

ensure_service_account() {
  if ! getent group "${SERVICE_GROUP}" >/dev/null; then
    log "Creating service group ${SERVICE_GROUP}"
    groupadd --gid "${SERVICE_UID}" "${SERVICE_GROUP}"
  fi

  if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
    log "Creating service user ${SERVICE_USER}"
    useradd \
      --uid "${SERVICE_UID}" \
      --gid "${SERVICE_GROUP}" \
      --home-dir "${BASE_DIR}" \
      --create-home \
      --shell /usr/sbin/nologin \
      "${SERVICE_USER}"
  fi

  usermod -L "${SERVICE_USER}" >/dev/null 2>&1 || true
}

ensure_directories() {
  log "Creating guest-local storage roots"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${BASE_DIR}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${QUARANTINE_DIR}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${ACCEPTED_DIR}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${REJECTED_DIR}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${STATE_DIR}"
  install -d -o "${SERVICE_USER}" -g "${SERVICE_GROUP}" -m 0750 "${LOG_DIR}"
}

configure_sshd() {
  log "Disabling password SSH login by default"
  install -d -m 0755 /etc/ssh/sshd_config.d
  cat >/etc/ssh/sshd_config.d/99-call-rating-ingestion.conf <<'EOF'
PermitRootLogin no
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
EOF

  sshd -t
  systemctl restart ssh || systemctl restart sshd
}

configure_firewall() {
  if [[ -z "${EGRESS_ALLOWED_CIDRS// }" ]]; then
    echo "Set EGRESS_ALLOWED_CIDRS to one or more space-separated CIDRs before enabling the firewall." >&2
    exit 1
  fi

  log "Configuring allowlisted firewall rules"
  ufw --force reset
  ufw default deny incoming
  ufw default deny outgoing

  if [[ -n "${SSH_ALLOWED_CIDR}" ]]; then
    ufw allow from "${SSH_ALLOWED_CIDR}" to any port 22 proto tcp
  fi

  # ponytail: UFW allowlists IPs, not domains; use fixed endpoint CIDRs or an egress proxy.
  for cidr in ${EGRESS_ALLOWED_CIDRS}; do
    ufw allow out to "${cidr}"
  done

  ufw --force enable
}

document_key_based_management() {
  install -d -m 0755 /etc/motd.d
  cat >/etc/motd.d/90-call-rating-ingestion 2>/dev/null <<EOF || true
Call recording ingestion VM

Management access is key-based SSH only.
Password SSH is disabled.
Egress is allowlisted with EGRESS_ALLOWED_CIDRS.
Keep shared folders, clipboard integration, drag-and-drop, USB passthrough, and host-drive mounts disabled.
EOF
}

main() {
  require_root

  log "Starting ingestion VM bootstrap"
  ensure_service_account
  ensure_directories
  install_packages
  configure_sshd
  configure_firewall
  document_key_based_management

  log "Bootstrap complete"
  log "Approved management route: key-based SSH only"
  log "Guest-local storage roots:"
  log "  ${QUARANTINE_DIR}"
  log "  ${ACCEPTED_DIR}"
  log "  ${REJECTED_DIR}"
  log "  ${STATE_DIR}"
  log "Allowlisted egress CIDRs: ${EGRESS_ALLOWED_CIDRS}"
  log "Do not enable host mounts or desktop integration features."
  log "Verify hypervisor settings remain NAT-only with shared folders, clipboard, drag-and-drop, USB passthrough, and host-drive mounts disabled."
  log "Record the baseline snapshot ID and validation date in docs/vm-isolation-verification.md before enabling ingestion."
}

main "$@"
