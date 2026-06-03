#!/usr/bin/env bash
# One-shot: pull all upstream base images and re-push them to Harbor under
# `library/`, so internal builds don't need to reach Docker Hub anymore.
#
# Run this from a machine that CAN reach Docker Hub (or a working mirror).
# If Docker Hub is blocked, set UPSTREAM_PREFIX to a reachable Docker Hub
# mirror, for example:
#   UPSTREAM_PREFIX=<dockerhub-mirror> ./stage-base-images.sh
# If images were loaded from tar files already, skip upstream pulls:
#   SKIP_PULL=1 ./stage-base-images.sh
# After it finishes, build with USE_STAGED_BASE_IMAGES=1 so Dockerfiles use
# the staged Harbor base images instead of Docker Hub.
set -euo pipefail

REGISTRY="${REGISTRY:-harbor.local:8088}"
PROJECT="${PROJECT:-library}"  # create the `library` project on Harbor first
UPSTREAM_PREFIX="${UPSTREAM_PREFIX:-}"
SKIP_PULL="${SKIP_PULL:-}"

# Bases required by backend/Dockerfile, ui/Dockerfile and the backend's
# wait-for-db init container. The Java (maven / eclipse-temurin) images are
# gone — security-server was ported into nemo-backend.
IMAGES=(
  "continuumio/miniconda3:latest"
  "node:20-alpine"
  "nginx:1.27-alpine"
  "bitnami/kubectl:1.30"
)

resolve_source_image() {
  local ref="$1"
  local image_name="${ref%%:*}"
  local upstream="${UPSTREAM_PREFIX%/}"

  if [[ -z "${upstream}" ]]; then
    echo "${ref}"
  elif [[ "${image_name}" == */* ]]; then
    echo "${upstream}/${ref}"
  else
    echo "${upstream}/library/${ref}"
  fi
}

echo "==> Logging in to ${REGISTRY}"
docker login "${REGISTRY}"

for ref in "${IMAGES[@]}"; do
  name="${ref%%:*}"
  tag="${ref##*:}"
  src="$(resolve_source_image "${ref}")"
  dst="${REGISTRY}/${PROJECT}/${name}:${tag}"

  echo
  if [[ -n "${SKIP_PULL}" ]]; then
    echo "==> Skipping pull for ${src}"
  else
    echo "==> Pulling ${src}"
    docker pull "${src}"
  fi

  echo "==> Tagging  ${dst}"
  docker tag "${src}" "${dst}"

  echo "==> Pushing  ${dst}"
  docker push "${dst}"
done

echo
echo "Done. Staged images:"
for ref in "${IMAGES[@]}"; do
  name="${ref%%:*}"
  tag="${ref##*:}"
  echo "  ${REGISTRY}/${PROJECT}/${name}:${tag}"
done
echo
echo "For project builds on restricted networks, set:"
echo "  USE_STAGED_BASE_IMAGES=1 BASE_PROJECT=${PROJECT}"
