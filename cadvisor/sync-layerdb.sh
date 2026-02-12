#!/bin/sh
# Synchronise le layerdb pour cAdvisor dans un environnement LXC Proxmox
# Docker dans LXC utilise /var/lib/docker/rootfs/overlayfs/ au lieu de
# /var/lib/docker/image/overlayfs/layerdb/mounts/ attendu par cAdvisor

LAYERDB="/var/lib/docker/image/overlayfs/layerdb/mounts"
ROOTFS="/var/lib/docker/rootfs/overlayfs"

mkdir -p "$LAYERDB"

# Synchroniser en boucle pour capturer les nouveaux conteneurs
while true; do
  for id in "$ROOTFS"/*/; do
    id=$(basename "$id")
    if [ ! -f "$LAYERDB/$id/mount-id" ]; then
      mkdir -p "$LAYERDB/$id"
      echo "$id" > "$LAYERDB/$id/mount-id"
      echo "[sync-layerdb] Added $id"
    fi
  done
  sleep 10
done
