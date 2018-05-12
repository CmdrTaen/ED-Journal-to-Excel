#!/usr/bin/env python

from __future__ import print_function
import argparse

from . import env
from . import pgnames
from . import util

app_name = "coords"

log = util.get_logger(app_name)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Display System Coordinates", fromfile_prefix_chars="@", parents=ap_parents, prog = app_name)
    ap.add_argument("system", metavar="system", type=str, nargs="*", help="The system to print the coordinates for")
    self.args = ap.parse_args(arg)

  def run(self):
    maxlen = 0
    with env.use() as envdata:
      systems = envdata.parse_systems(self.args.system)
      for name in self.args.system:
        maxlen = max(maxlen, len(name))
        if name not in systems or systems[name] is None:
          pgsys = pgnames.get_system(name)
          if pgsys is not None:
            systems[name] = pgsys
          else:
            log.error("Could not find system \"{0}\"!", name)
            return

    print("")
    for name in self.args.system:
      s = systems[name]
      fmtstr = "  {0:>" + str(maxlen) + "s}: [{1:>8.2f}, {2:>8.2f}, {3:>8.2f}]"
      extrastr = " +/- {0:.0f}LY in each axis".format(s.uncertainty) if s.uncertainty != 0.0 else ""
      print(fmtstr.format(name, s.position.x, s.position.y, s.position.z) + extrastr)
    print("")

    return True
