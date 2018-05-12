#!/usr/bin/env python

from __future__ import print_function
import argparse
import sys

from . import env
from . import util
from . import vector3

app_name = "direction"

log = util.get_logger(app_name)

class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Calculate direction between two systems", fromfile_prefix_chars="@", parents = ap_parents, prog = app_name)
    ap.add_argument("-a", "--angle", default=False, action='store_true', help="Return angle not vector")
    ap.add_argument("-c", "--check", default=False, action='store_true', help="Check if second system is in the same direction as the first from the reference")
    ap.add_argument("-n", "--normal", default=False, action='store_true', help="Return normalised direction vector")
    ap.add_argument("-r", "--reference", metavar="system", nargs='?', default="Sol", help="Reference system for angle calculation")
    ap.add_argument("-t", "--tolerance", type=float, default=5, help="Tolerance in percent for --check")
    ap.add_argument("systems", metavar="system", nargs=2, help="Systems")

    self.args = ap.parse_args(arg)
    if self.args.tolerance is not None:
      if self.args.tolerance < 0 or self.args.tolerance > 100:
        log.error("Tolerance must be in range 0 to 100 (percent)!")
        sys.exit(1)

  def run(self):
    with env.use() as envdata:
      systems = envdata.parse_systems(self.args.systems)
      for y in self.args.systems:
        if y not in systems or systems[y] is None:
          log.error("Could not find system \"{0}\"!", y)
          return

      if self.args.reference:
        reference = envdata.parse_system(self.args.reference)
        if reference is None:
          log.error("Could not find reference system \"{0}\"!", self.args.reference)
          return

      a, b = [systems[y].position for y in self.args.systems]
      if self.args.check:
        v = (a - reference.position).get_normalised()
        w = (b - reference.position).get_normalised()
        d = v.dot(w)
        log.debug('{0} vs {1} dot {2}', v, w, d)
        if d >= 1.0 - float(self.args.tolerance) / 100:
          print('OK {0:.2f}% deviation'.format(100 * (1 - d)))
          sys.exit(0)
        elif d < 0.0:
          print('NO opposite')
        else:
          print('NO {0:.2f}% deviation'.format(100 * (1 - d)))
        sys.exit(100)
      else:
        v = b - a
        log.debug("From {0} to {1}", a, b)

        if self.args.angle:
          print(v.angle_to(a - reference.position))
        elif self.args.normal:
          log.debug("Normalising {0}", v)
          print(v.get_normalised())
        else:
          print(v)
