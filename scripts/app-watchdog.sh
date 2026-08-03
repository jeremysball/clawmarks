#!/bin/sh
# Restarts the app service in response to two conditions Docker's own restart policy doesn't
# cover on its own: a tailscale sidecar restart, or app reporting unhealthy.
set -eu

# PROJECT must be pinned (via the PROJECT_NAME env var) rather than discovered
# from running containers — the docker.sock this reads from is host-wide, and
# other compose projects on the same host may run their own service also
# labeled "tailscale", which a label-only lookup would match by mistake.
: "${PROJECT_NAME:?PROJECT_NAME env var must be set}"
PROJECT="$PROJECT_NAME"
# The service that joins tailscale's netns isn't always literally named "app"
# (e.g. alfred, dashboard) — override via APP_SERVICE_NAME when porting this.
APP_SERVICE_NAME="${APP_SERVICE_NAME:-app}"

restart_app() {
  reason="$1"
  APP_CID=$(docker ps -q --filter "label=com.docker.compose.service=$APP_SERVICE_NAME" --filter "label=com.docker.compose.project=$PROJECT")
  if [ -n "$APP_CID" ]; then
    echo "app-watchdog: $reason, restarting $APP_SERVICE_NAME ($APP_CID)"
    docker restart "$APP_CID"
  else
    echo "app-watchdog: $reason but no $APP_SERVICE_NAME container found to restart"
  fi
}

echo "app-watchdog: watching for tailscale restarts and $APP_SERVICE_NAME unhealthy status (project=$PROJECT, app service=$APP_SERVICE_NAME)"

# `app` joins tailscale's network namespace via `network_mode: service:tailscale`, but that join
# only happens once, at app's own container start. If tailscale restarts in place (crash, OOM,
# `restart: always`), it gets a fresh network namespace and app is left bound to the old,
# orphaned one — silently unreachable even though both containers report "running". Restarting
# app re-joins whatever namespace tailscale currently has.
#
# We watch for `start` rather than `restart`: Docker only emits a `restart`-typed event for an
# explicit `docker restart` command. A restart-policy-triggered relaunch (crash, OOM, or the
# plain `restart: always` policy after a clean exit) shows up as a `die` followed by a `start` —
# confirmed via `journalctl -u docker` logging `"restarting container" manualRestart=false` for
# exactly this case. `event=restart` alone misses that path entirely, which is how this watchdog
# failed to fire the one time it mattered (see hearth's fix/tailscale-netns-watchdog and
# fix/netns-watchdog-catch-policy-restarts).
# The `docker events | while read` pipeline restarts on its own exit (daemon hiccup, transient
# filter rejection) instead of just dying, so a momentary `docker events` failure doesn't leave
# this watcher permanently blind under `set -e` in dash.
while true; do
  docker events --filter 'event=start' \
    --filter "label=com.docker.compose.service=tailscale" \
    --filter "label=com.docker.compose.project=$PROJECT" \
    --format '{{.Actor.Attributes.name}}' |
  while read -r _; do
    restart_app "tailscale restarted"
  done
  echo "app-watchdog: tailscale event stream ended, restarting watcher"
  sleep 1
done &

# app's own HEALTHCHECK can go unhealthy without the process ever exiting — a stuck accept loop
# still holds the port open, so plain `restart: unless-stopped` never fires. This is the gap that
# let a bad deploy sit unreachable with nothing auto-recovering it (see hearth's
# fix/app-healthcheck-and-watchdog-restart).
while true; do
  docker events --filter 'event=health_status: unhealthy' \
    --filter "label=com.docker.compose.service=$APP_SERVICE_NAME" \
    --filter "label=com.docker.compose.project=$PROJECT" \
    --format '{{.Actor.Attributes.name}}' |
  while read -r _; do
    restart_app "$APP_SERVICE_NAME reported unhealthy"
  done
  echo "app-watchdog: health event stream ended, restarting watcher"
  sleep 1
done &

wait
