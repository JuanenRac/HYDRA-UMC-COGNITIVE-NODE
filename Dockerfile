# =============================================================================
# HYDRA-UMC-COGNITIVE-NODE - Container Build: Dockerfile
# Copyright (C) 2026 JuanenRac (Electro Hobby 3D) <electrohobby3d@gmail.com>
# GPL-3.0 - see LICENSE
# =============================================================================
# Real, minimal image for the family-readiness HTTP API (api.py's own
# server, stdlib http.server - pyproject.toml's own dependencies is
# deliberately []). Same --addr/--port CLI the real CM5 systemd unit
# (systemd/hydra-umc-cognitive-node.service) already runs, just bound to
# 0.0.0.0 instead of 127.0.0.1 here - a container's own network namespace
# already isolates it the way the systemd unit's loopback bind does on
# bare metal. Non-root, matching that same unit's own
# User=hydra-umc-cognitive-node. This is this repo's OWN Dockerfile - its
# 4 children (voice-ui/semantic-planner/vla-engine/docs-qa) each ship
# their own already; this one was the real remaining gap `docker-compose.yml`'s
# own `cognitive-node` service (`build: .`) needed to actually build.
#
# After `pip install .` the package lives in site-packages, so the default
# "parent of the repository" no longer points at the sibling checkouts or at
# models/. The workspace and the weights directory are therefore passed
# explicitly (docker-compose.yml mounts the four children's manifests under
# /workspace and the weights under /opt/hydra/models). On bare metal the
# install script of HYDRA-UMC-OS provisions the same files for the systemd unit.

FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE.md ./
COPY src ./src
RUN pip install --no-cache-dir .

RUN useradd --system --create-home --home-dir /home/hydra hydra
USER hydra

EXPOSE 8096
ENTRYPOINT ["hydra-umc-cognitive-node"]
CMD ["serve", "--addr", "0.0.0.0", "--port", "8096", "--workspace", "/workspace", "--models-dir", "/opt/hydra/models"]
