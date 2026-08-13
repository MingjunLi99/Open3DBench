#!/bin/bash

set -euo pipefail

failures=0

check() {
    local description=$1
    shift
    if "$@" >/dev/null 2>&1; then
        echo "[OK] ${description}"
    else
        echo "[FAIL] ${description}" >&2
        failures=$((failures + 1))
    fi
}

check_free_space() {
    local available_kib
    available_kib=$(df -Pk / | awk 'NR == 2 {print $4}')
    [[ "${available_kib}" =~ ^[0-9]+$ ]] && (( available_kib >= 104857600 ))
}

echo "Open3DBench offline host check"
echo "  kernel: $(uname -r)"
echo "  arch:   $(uname -m)"
echo "  pid 1:  $(ps -p 1 -o comm= 2>/dev/null || echo unknown)"
echo "  rootfs: $(df -T / | awk 'NR == 2 {print $2, $5 " KiB free"}')"

check "x86_64 architecture" test "$(uname -m)" = x86_64
check "WSL2 kernel" sh -c 'uname -r | grep -qi microsoft-standard-WSL2'
check "cgroup v2" test -f /sys/fs/cgroup/cgroup.controllers
check "overlay filesystem support" sh -c 'grep -qw overlay /proc/filesystems'
check "at least 100 GiB free" check_free_space

if command -v docker >/dev/null 2>&1; then
    docker_version=$(docker version --format '{{.Client.Version}}' 2>/dev/null || true)
    echo "  docker client: ${docker_version:-unavailable}"
    if [[ "${docker_version}" == 1.13.* ]]; then
        echo "[FAIL] Docker 1.13 is unsupported; install the bundled Docker 26 static release." >&2
        failures=$((failures + 1))
    fi
else
    echo "[INFO] Docker is not installed yet."
fi

if (( failures > 0 )); then
    echo "Host check failed: ${failures} issue(s)." >&2
    exit 1
fi

echo "Host check passed."
