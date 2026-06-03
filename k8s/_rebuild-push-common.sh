#!/usr/bin/env bash
# Shared implementation for rebuilding and pushing one project image.
set -euo pipefail

REGISTRY="${REGISTRY:-harbor.local:8088}"
PROJECT="${PROJECT:-oppointments-system}"
TAG="${TAG:-latest}"
LOGIN="${LOGIN:-1}"
USE_CN_BASE_IMAGES="${USE_CN_BASE_IMAGES:-1}"
CN_BASE_REGISTRY="${CN_BASE_REGISTRY:-docker.1panel.live}"

BACKEND_BASE_IMAGE="${BACKEND_BASE_IMAGE:-}"
NODE_BASE_IMAGE="${NODE_BASE_IMAGE:-}"
NGINX_BASE_IMAGE="${NGINX_BASE_IMAGE:-}"

if [[ "${USE_CN_BASE_IMAGES}" == "1" ]]; then
  BACKEND_BASE_IMAGE="${BACKEND_BASE_IMAGE:-${CN_BASE_REGISTRY}/continuumio/miniconda3:latest}"
  NODE_BASE_IMAGE="${NODE_BASE_IMAGE:-${CN_BASE_REGISTRY}/library/node:20-alpine}"
  NGINX_BASE_IMAGE="${NGINX_BASE_IMAGE:-${CN_BASE_REGISTRY}/library/nginx:1.27-alpine}"
fi

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <nemo-backend|nemo-ui>" >&2
  exit 2
fi

name="$1"
context=""
dockerfile=""
container=""
deployment=""
build_args=()

case "${name}" in
  nemo-backend)
    context="${REPO_ROOT}/backend"
    dockerfile="${REPO_ROOT}/backend/Dockerfile"
    deployment="nemo-backend"
    container="backend"
    [[ -n "${BACKEND_BASE_IMAGE}" ]] && build_args+=(--build-arg "BASE_IMAGE=${BACKEND_BASE_IMAGE}")
    ;;
  nemo-ui)
    # Single SPA image; staff routes are bundled into the same dist under
    # /security/* (vue-router). Context is just ui/.
    context="${REPO_ROOT}/ui"
    dockerfile="${REPO_ROOT}/ui/Dockerfile"
    deployment="nemo-ui"
    container="ui"
    [[ -n "${NODE_BASE_IMAGE}" ]] && build_args+=(--build-arg "NODE_BASE_IMAGE=${NODE_BASE_IMAGE}")
    [[ -n "${NGINX_BASE_IMAGE}" ]] && build_args+=(--build-arg "NGINX_BASE_IMAGE=${NGINX_BASE_IMAGE}")
    ;;
  *)
    echo "Unknown image: ${name}" >&2
    echo "(security-server / security-server-ui are gone; both are now folded into nemo-backend / nemo-ui.)" >&2
    exit 2
    ;;
esac

image="${REGISTRY}/${PROJECT}/${name}:${TAG}"

if [[ "${LOGIN}" == "1" ]]; then
  echo "==> docker login ${REGISTRY}"
  docker login "${REGISTRY}"
fi

echo "==> Building ${image}"
docker build "${build_args[@]}" -f "${dockerfile}" -t "${image}" "${context}"

echo "==> Pushing ${image}"
docker push "${image}"

echo
echo "Pushed: ${image}"
echo "Deploy with:"
echo "  kubectl -n nemo set image deploy/${deployment} ${container}=${image}"
echo "  kubectl -n nemo rollout status deploy/${deployment}"
