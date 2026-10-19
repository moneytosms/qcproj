#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
if [ -d data/takaishi ]; then
  echo "data/takaishi already exists"
  exit 0
fi
git clone --depth 1 https://github.com/takaishi-physics/QCL-volatility.git data/takaishi
rm -rf data/takaishi/.git
echo "Downloaded Takaishi's Bitcoin data into data/takaishi"
