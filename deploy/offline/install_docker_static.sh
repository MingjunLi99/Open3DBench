#!/bin/bash

set -euo pipefail

usage() {
    echo "Usage: sudo $0 <docker-static-x86_64.tgz>"
}

if [[ $# -ne 1 ]]; then
    usage >&2
    exit 2
fi

if [[ ${EUID} -ne 0 ]]; then
    echo "Run this installer as root." >&2
    exit 1
fi

archive=$(readlink -f "$1")
if [[ ! -s "${archive}" ]]; then
    echo "Docker archive not found or empty: ${archive}" >&2
    exit 1
fi

if [[ $(uname -m) != x86_64 ]]; then
    echo "This package supports x86_64 only." >&2
    exit 1
fi

if command -v docker >/dev/null 2>&1; then
    installed_version=$(docker version --format '{{.Client.Version}}' 2>/dev/null || true)
    if [[ -n "${installed_version}" && "${installed_version}" != 1.13.* ]]; then
        echo "Docker client already installed (${installed_version}); refusing to overwrite it." >&2
        exit 1
    fi
fi

work_dir=$(mktemp -d /tmp/open3dbench-docker-install.XXXXXX)
trap 'rm -rf "${work_dir}"' EXIT

tar -xzf "${archive}" -C "${work_dir}"

required=(docker dockerd containerd containerd-shim-runc-v2 ctr runc docker-init docker-proxy)
for binary in "${required[@]}"; do
    if [[ ! -x "${work_dir}/docker/${binary}" ]]; then
        echo "Missing binary in Docker archive: ${binary}" >&2
        exit 1
    fi
done

version=$(${work_dir}/docker/docker --version | awk '{print $3}' | tr -d ',')
install_root="/opt/docker-${version}"

if [[ -e "${install_root}" ]]; then
    echo "Install directory already exists: ${install_root}" >&2
    exit 1
fi

install -d -m 0755 "${install_root}" /usr/local/bin /var/lib/docker /var/log/docker
for binary in "${required[@]}"; do
    install -m 0755 "${work_dir}/docker/${binary}" "${install_root}/${binary}"
    ln -sfn "${install_root}/${binary}" "/usr/local/bin/${binary}"
done

echo "Installed Docker ${version} under ${install_root}."
echo "Start the daemon with deploy/offline/start_docker_wsl.sh."
