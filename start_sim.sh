#!/usr/bin/env bash
# G1 23-DoF simulator for study: domain 1 on lo, elastic band holds the robot up.
# Needs lo multicast after every reboot: sudo ip link set lo multicast on
if ! ip link show lo | grep -q MULTICAST; then
  echo "lo multicast is off: run  sudo ip link set lo multicast on" >&2; exit 1
fi
cd "$(dirname "$0")/sim/build"
exec env -u CYCLONEDDS_URI LD_LIBRARY_PATH=/opt/unitree_robotics/lib ./unitree_mujoco
