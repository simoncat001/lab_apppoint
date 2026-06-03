#!/usr/bin/env bash
# Build the project images and push them to a private Harbor registry.
#
# Only two images now:
#   - nemo-backend (FastAPI, also serves the ported security-server endpoints
#     at /security-api/api/*)
#   - nemo-ui (single nginx image; vue-router serves nemo at / and the
#     ported staff SPA at /security/* from one bundled dist)
#
# Usage:
#   ./build-and-push.sh                 # tags as :latest
#   TAG=v0.1.0 ./build-and-push.sh      # custom tag
#   USE_STAGED_BASE_IMAGES=1 ./build-and-push.sh   # use Harbor-staged bases
set -euo pipefail

REGISTRY="${REGISTRY:-harbor.local:8088}"
PROJECT="${PROJECT:-oppointments-system}"
TAG="${TAG:-latest}"
BASE_PROJECT="${BASE_PROJECT:-library}"
USE_STAGED_BASE_IMAGES="${USE_STAGED_BASE_IMAGES:-}"
BACKEND_BASE_IMAGE="${BACKEND_BASE_IMAGE:-}"
NODE_BASE_IMAGE="${NODE_BASE_IMAGE:-}"
NGINX_BASE_IMAGE="${NGINX_BASE_IMAGE:-}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -n "${USE_STAGED_BASE_IMAGES}" ]]; then
  BACKEND_BASE_IMAGE="${BACKEND_BASE_IMAGE:-${REGISTRY}/${BASE_PROJECT}/continuumio/miniconda3:latest}"
  NODE_BASE_IMAGE="${NODE_BASE_IMAGE:-${REGISTRY}/${BASE_PROJECT}/node:20-alpine}"
  NGINX_BASE_IMAGE="${NGINX_BASE_IMAGE:-${REGISTRY}/${BASE_PROJECT}/nginx:1.27-alpine}"
fi

echo "==> Logging in to ${REGISTRY}"
docker login "${REGISTRY}"

build_one() {
  local name="$1"
  local context="$2"
  local dockerfile="$3"
  shift 3
  local -a build_args=("$@")
  local image="${REGISTRY}/${PROJECT}/${name}:${TAG}"

  echo
  echo "==> Building ${image}"
  docker build "${build_args[@]}" -f "${dockerfile}" -t "${image}" "${context}"
  echo "==> Pushing  ${image}"
  docker push "${image}"
}

# ---------- nemo-backend ----------
backend_args=()
[[ -n "${BACKEND_BASE_IMAGE}" ]] && backend_args+=(--build-arg "BASE_IMAGE=${BACKEND_BASE_IMAGE}")
build_one "nemo-backend" "${REPO_ROOT}/backend" "${REPO_ROOT}/backend/Dockerfile" "${backend_args[@]}"

# ---------- nemo-ui (single SPA, bundles staff routes under /security/*) ----------
ui_args=()
[[ -n "${NODE_BASE_IMAGE}" ]]  && ui_args+=(--build-arg "NODE_BASE_IMAGE=${NODE_BASE_IMAGE}")
[[ -n "${NGINX_BASE_IMAGE}" ]] && ui_args+=(--build-arg "NGINX_BASE_IMAGE=${NGINX_BASE_IMAGE}")
build_one "nemo-ui" "${REPO_ROOT}/ui" "${REPO_ROOT}/ui/Dockerfile" "${ui_args[@]}"

echo
echo "All images pushed:"
echo "  ${REGISTRY}/${PROJECT}/nemo-backend:${TAG}"
echo "  ${REGISTRY}/${PROJECT}/nemo-ui:${TAG}"
