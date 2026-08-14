#!/bin/bash

set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
    echo "Run this script as root." >&2
    exit 1
fi

if ! command -v dockerd >/dev/null 2>&1 || ! command -v docker >/dev/null 2>&1; then
    echo "Docker static binaries are not installed." >&2
    exit 1
fi

if docker info >/dev/null 2>&1; then
    echo "Docker daemon is already running."
    docker version
    exit 0
fi

install -d -m 0755 /var/lib/docker /var/log/docker /var/run
log_file=/var/log/docker/dockerd-open3dbench.log

# The deployment containers use --network none. Disabling Docker networking
# avoids obsolete CentOS 7 iptables integration and enforces offline execution.
nohup dockerd \
    --host=unix:///var/run/docker.sock \
    --data-root=/var/lib/docker \
    --exec-root=/var/run/docker \
    --pidfile=/var/run/docker-open3dbench.pid \
    --storage-driver=overlay2 \
    --bridge=none \
    --iptables=false \
    --ip-masq=false \
    --userland-proxy=false \
    ${DOCKERD_EXTRA_ARGS:-} \
    >"${log_file}" 2>&1 &

for _ in $(seq 1 30); do
    if docker info >/dev/null 2>&1; then
        echo "Docker daemon started in offline-only mode."
        docker version
        exit 0
    fi
    sleep 1
done

echo "Docker daemon did not become ready. Log: ${log_file}" >&2
tail -100 "${log_file}" >&2 || true
exit 1
