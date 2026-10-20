#!/usr/bin/env bash
# Download the pinned Bitstamp BTC/USD 1-minute data used by the fresh-data study.
# Source: https://github.com/ff137/bitstamp-btcusd-minute-data (data CC BY-SA 4.0 / CC BY 4.0).
set -euo pipefail
COMMIT=c711b69cdcffd1356247126b1e0f53455efb70ba
DEST=${1:-.cache/bitstamp-minute}
if [ -d "$DEST/.git" ]; then
  echo "$DEST already exists"
  exit 0
fi
mkdir -p "$DEST"
git -C "$DEST" init -q
git -C "$DEST" remote add origin https://github.com/ff137/bitstamp-btcusd-minute-data.git
git -C "$DEST" fetch -q --depth 1 origin "$COMMIT"
git -C "$DEST" checkout -q FETCH_HEAD
echo "Bitstamp minute data at $DEST (commit $COMMIT)"
