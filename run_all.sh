#!/usr/bin/env bash
# Runs the whole project in order. The first run downloads the event files into data/.
set -e
for s in part0_data_audit part1_dominance part1b_charts part2_escapes part2b_chart \
         part3_style part3b_chart part4_players part4b_chart checks; do
  echo "== $s"
  python "$s.py"
done
