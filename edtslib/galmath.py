#!/usr/bin/env python

from __future__ import print_function
import argparse
import math
import sys

from . import util

app_name = "galmath"

log = util.get_logger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap = argparse.ArgumentParser(description = "Magic Number plotting for the Galactic Core", fromfile_prefix_chars="@", prog = app_name)
    ap.add_argument("-j", "--jump-range", required=('ship' not in state), type=float, help="The full jump range of the ship")
    ap.add_argument("-c", "--core-distance", required=True, type=float, help="Current distance from the centre of the core (Sagittarius A*) in kLY")
    ap.add_argument("-d", "--distance", required=False, type=float, default=1000.0, help="The distance to travel")
    self.args = ap.parse_args(arg)

    if self.args.jump_range is None:
      if 'ship' in state:
        self.args.jump_range = state['ship'].range()
      else:
        raise Exception("Jump range not provided and no ship previously set")

  def run(self):
    num_jumps = int(math.floor(self.args.distance / self.args.jump_range))
    low_max_dist = num_jumps * self.args.jump_range

    ans = low_max_dist - ((num_jumps / 4.0) + ((self.args.core_distance + 1) * 2.0))
    inaccuracy = low_max_dist * 0.0025

    log.debug("M = {0:.2f}, N = {1}, D = {2:.2f}", low_max_dist, num_jumps, self.args.core_distance)

    print("")
    print("Travelling {0:.1f}LY with a {1:.2f}LY jump range, at around {2:.0f}LY from the core centre:".format(
          self.args.distance,
          self.args.jump_range,
          self.args.core_distance * 1000.0))
    print("")
    print("  Maximum jump in range: {0:.1f}LY".format(low_max_dist))
    print("  Plot between {0:.1f}LY and {1:.1f}LY".format(ans - inaccuracy, ans + inaccuracy))
    print("")

    return True
