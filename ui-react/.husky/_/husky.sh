#!/bin/sh
if [ -z "$husky_skip_init" ]; then
  debug () {
    [ "$HUSKY_DEBUG" = "1" ] && echo "husky: $*"
  }
  readonly hookname="$(basename "$0")"
  debug "starting $hookname..."
  if [ "$HUSKY" = "0" ]; then
    debug "HUSKY env variable is set to 0, skipping hook" && exit 0
  fi
  if [ -f ~/.huskyrc ]; then
    debug "sourcing ~/.huskyrc"
    . ~/.huskyrc
  fi
  export readonly husky_skip_init=1
  sh -e "$0" "$@"
  exitCode=$?
  debug "finished $hookname, exit code $exitCode"
  exit $exitCode
fi
