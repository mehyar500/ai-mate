#!/usr/bin/env bash
# Amorien — domain availability checker.
# Queries authoritative registry RDAP endpoints. 404 = available, 200 = registered.
# Usage:  ./scripts/check-domains.sh names.txt
#         echo amorien | ./scripts/check-domains.sh
set -uo pipefail

check() {
  local n="$1" t="$2" url
  case "$t" in
    com|net) url="https://rdap.verisign.com/$t/v1/domain/$n.$t" ;;
    ai)      url="https://rdap.identitydigital.services/rdap/domain/$n.ai" ;;
    *)       url="https://rdap.org/domain/$n.$t" ;;
  esac
  local code
  for _ in 1 2 3 4; do
    code=$(curl -sL -o /dev/null -m 20 -w "%{http_code}" "$url")
    case "$code" in 200|404) break ;; esac
    sleep 3
  done
  case "$code" in
    404) printf 'FREE   %s.%s\n'  "$n" "$t" ;;
    200) printf 'taken  %s.%s\n'  "$n" "$t" ;;
    *)   printf '?%-5s %s.%s\n'   "$code" "$n" "$t" ;;
  esac
}

TLDS="${TLDS:-com ai}"
SRC="${1:--}"
while read -r name; do
  [ -z "$name" ] && continue
  for tld in $TLDS; do check "$name" "$tld"; done
done < "$SRC"
