#!/usr/bin/env bash
# Download Cricsheet's T20 international ball-by-ball data (CSV2 format) into data/t20s_csv2/.
#
# Cricsheet updates this file as new matches are played, so a fresh download will
# include matches after 26 July 2025, the cut-off used in the write-ups.
set -euo pipefail

cd "$(dirname "$0")/.."
mkdir -p data

curl -fL --progress-bar -o data/t20s_csv2.zip https://cricsheet.org/downloads/t20s_csv2.zip
unzip -oq data/t20s_csv2.zip -d data/t20s_csv2

echo "Unpacked $(find data/t20s_csv2 -name '*_info.csv' | wc -l) matches into data/t20s_csv2/"
