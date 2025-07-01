#!/bin/sh
# wait-for-it.sh - v2.2.3

# This script is a simplified version of the original wait-for-it.sh by vishnubob
# Full version: https://github.com/vishnubob/wait-for-it

set -e

TIMEOUT=30
QUIET=0
HOST=
PORT=

usage() {
    echo "Usage: $0 host:port [-t timeout] [-- command args]"
    exit 1
}

while [ $# -gt 0 ]
do
    case "$1" in
        *:* )
        HOST=$(printf "%s\n" "$1"| cut -d : -f 1)
        PORT=$(printf "%s\n" "$1"| cut -d : -f 2)
        shift 1
        ;;
        -q)
        QUIET=1
        shift 1
        ;;
        -t)
        TIMEOUT="$2"
        if [ "$TIMEOUT" = "" ]; then break; fi
        shift 2
        ;;
        --)
        shift
        break
        ;;
        *)
        usage
        ;;
    esac
done

if [ "$HOST" = "" ] || [ "$PORT" = "" ]; then
    echo "Error: you need to provide a host and port to test."
    usage
fi

CMD=$@

wait_for() {
    if [ "$QUIET" -eq 0 ]; then echo "Waiting for $HOST:$PORT..."; fi
    for i in `seq $TIMEOUT` ; do
        nc -z "$HOST" "$PORT" > /dev/null 2>&1
        result=$?
        if [ $result -eq 0 ] ; then
            if [ $# -gt 0 ] ; then
                if [ "$QUIET" -eq 0 ]; then echo "Connection to $HOST:$PORT is up. Executing command: $CMD"; fi
                exec $CMD
            fi
            exit 0
        fi
        sleep 1
    done
    echo "Operation timed out" >&2
    exit 1
}

wait_for