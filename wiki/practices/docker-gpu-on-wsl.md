---
type: practice
title: Give Docker GPU access on WSL2
aliases: [docker-gpu-wsl, nvidia-container-toolkit-wsl]
tags: [tooling, wsl, docker]
created: 2026-07-03
updated: 2026-07-03
status: seed
related: ["[[obsidian-cli-on-wsl]]"]
---

# Give Docker GPU access on WSL2

How to fix `could not select device driver "nvidia" with capabilities: [[gpu]]` when a Compose
service (or `docker run --gpus all`) asks for a GPU on **WSL2 running native `dockerd`** (not Docker
Desktop).

## The mental model — two independent layers

GPU-in-container needs **both**, and they fail independently:

1. **The GPU is visible inside WSL.** Provided by the Windows NVIDIA driver + WSL's GPU passthrough.
   Test: `nvidia-smi` inside WSL prints the card. This is the hard part and usually already works.
2. **Docker has an `nvidia` runtime to hand the GPU to a container.** Provided by the **NVIDIA
   Container Toolkit**, installed *inside the WSL distro*. This is the part people miss.

The Compose GPU request (`deploy.resources.reservations.devices: [{driver: nvidia, capabilities:
[gpu]}]`) is correct and unchanged — the error means **layer 2 is missing**, so the daemon has no
`nvidia` driver to satisfy the request. **A working `nvidia-smi` is necessary but not sufficient** —
it only proves layer 1. ^[inferred]

## Diagnose before installing

```bash
nvidia-smi                                 # layer 1: prints the card?  (should already work)
which nvidia-ctk nvidia-container-runtime  # layer 2: installed?  (missing == the bug)
docker info | grep -i runtime              # is 'nvidia' a registered runtime? (only 'runc' == the bug)
```

If `nvidia-smi` works but the toolkit is absent and Docker lists only `runc`, layer 2 is your fix.

## Fix — install the toolkit and register the runtime

This is a one-time **host** change in the WSL distro; needs `sudo`. On Ubuntu/Debian:

```bash
# 1. Add NVIDIA's toolkit apt repo (distro-agnostic 'stable/deb' list)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
  | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
  | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
  | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# 2. Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# 3. Register the nvidia runtime with Docker + restart the daemon
sudo nvidia-ctk runtime configure --runtime=docker   # writes /etc/docker/daemon.json
sudo systemctl restart docker    # no systemd in this WSL distro? -> sudo service docker restart
```

`nvidia-ctk runtime configure` is what creates `/etc/docker/daemon.json` and adds the `nvidia`
runtime; its absence is why `docker info` showed only `runc`.

## Verify

```bash
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi
```

Prints the GPU table from *inside* a container → both layers are up, and `docker compose up --build`
will now satisfy the GPU reservation.

## Gotchas

- **Don't touch the Windows/WSL NVIDIA driver** if `nvidia-smi` already works in WSL — layer 1 is
  fine; the toolkit is purely container-side glue.
- **Docker Desktop is different.** With Desktop's WSL integration the runtime is wired for you; this
  recipe is for a **native `dockerd`** running inside the distro (`ps aux | grep dockerd`). ^[inferred]
- On a **very new distro release**, the `stable/deb` list may not yet resolve the package; fall back
  to NVIDIA's `experimental` list or a pinned `$distribution`. ^[inferred]
- If you don't need the GPU path at all, a **CPU/fake fallback stack** (where the GPU service is
  swapped for a non-GPU implementation) sidesteps the toolkit entirely — reach for the toolkit only
  when you actually need the real GPU workload in a container.

---

*Provenance: distilled from a hands-on debugging session — the diagnosis commands and their output
were run live on Ubuntu 26.04 under WSL2 with native `dockerd`, driver 581.95.*
