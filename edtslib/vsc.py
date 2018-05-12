#!/usr/bin/env python

from __future__ import print_function
import argparse
import os
import shutil
import sys
import time

from . import env
from . import filtering
from . import starcache
from . import util

app_name = "vsc"

log = util.get_logger(app_name)

class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap_parents = [env.arg_parser] if not hosted else []
    ap = argparse.ArgumentParser(description = "Read and write the visited stars cache", fromfile_prefix_chars="@", parents = ap_parents, prog = app_name)
    subparsers = ap.add_subparsers()
    bp = subparsers.add_parser("batch", help="Batch import jobs")
    bp.add_argument("-c", "--clean", default=False, action="store_true", help="Delete any existing cache rather than back it up")
    bp.add_argument("-d", "--directory", help="Directory where Elite looks for ImportStars.txt")
    bp.add_argument("-n", "--no-import", default=False, action="store_true", help="Only create ImportStars files, don't copy to game client")
    bp.add_argument("starfile", metavar="filename")
    bp.add_argument("dictfile", nargs='?', help="Destination file")
    bp.set_defaults(func=self.run_batch)
    ip = subparsers.add_parser("import", help="Use Elite client to run import job")
    ip.add_argument("-c", "--clean", default=False, action="store_true", help="Delete any existing cache rather than back it up")
    ip.add_argument("-d", "--directory", help="Directory where Elite looks for ImportStars.txt")
    ip.add_argument("importfile", metavar="filename")
    ip.add_argument("cachefile")
    ip.set_defaults(func=self.run_import)
    rp = subparsers.add_parser("read", help="Read from star cache")
    rp.add_argument("readfile", metavar="filename")
    rp.set_defaults(func=self.run_read)
    wp = subparsers.add_parser("write", help="Write to star cache")
    wp.add_argument("writefile", metavar="filename")
    wp.add_argument("-i", "--importfile", metavar="filename", nargs='?', help="File with list of stars")
    wp.add_argument("-r", "--recent", default=False, action="store_true", help="Create in RecentlyVisitedStars format")
    wp.add_argument("filters", metavar="filters", nargs='*')
    wp.set_defaults(func=self.run_write)

    self.args = ap.parse_args(arg)

  def run(self):
    with env.use() as envdata:
      self.args.func(envdata, self.args)

  def batch_read(self, envdata, id64list):
    missing = { str(id64): True for id64 in id64list }
    for s in envdata.find_systems_by_id64(id64list):
      print(s.name)
      id64 = str(s.id64)
      if id64 in missing:
        del(missing[id64])
    for id64 in missing.keys():
      print(id64)

  def run_batch(self, envdata, args):
    data = []
    with open(args.starfile, 'r') as f:
      for d in f:
        data.append(d.strip())

    if not len(data):
      log.warning("No stars in {}...", args.starfile)
      return

    cacheformat = 'VisitedStarsCache{}.dat'
    importformat = starcache.IMPORTFORMAT
    names = starcache.create_import_list_files(data, importformat)
    for name in names:
      cachefile = cacheformat.format(name)
      importfile = importformat.format(name)
      if args.no_import:
        print(format(importfile))
        continue
      log.info("Importing from {}", importfile)
      self.game_import({
        'cachefile': cachefile,
        'clean': args.clean,
        'directory': args.directory,
        'importfile': importfile
      })
      log.info("Import from {} complete", importfile)

    try:
      id64s = starcache.calculate_id64s_from_list_files(args.starfile, cacheformat.format('Full'), [cacheformat.format(n) for n in names if n != 'Full'])
    except IOError:
      if args.no_import:
        return
      log.error("Import job failed!")
      sys.exit(1)
    if args.dictfile:
      with open(args.dictfile, 'w') as f:
        f.write("known_systems = {\n")
        for name, id in id64s.items():
          f.write('  "{}": {},\n'.format(name, id))
        f.write("}\n")
    else:
      print(id64s)

  def client_import(self, importsrc, importdst, imported, recent):
    try:
      log.debug("Writing {}...", importdst)
      shutil.copyfile(importsrc, importdst)
      spoke = False
      while not os.path.isfile(recent):
        time.sleep(1)
        if not spoke:
          log.info("Waiting for game client to log in...")
          spoke = True
      spoke = False
      while os.path.isfile(importdst):
        time.sleep(1)
        if not spoke:
          log.info("Waiting for import job")
          spoke = True
      spoke = False
      while os.path.isfile(recent):
        time.sleep(1)
        if not spoke:
          log.info("Waiting for game client to log out...")
          spoke = True
    except IOError:
      log.error("Failed to copy {} to {}", importsrc, importdst)
    except KeyboardInterrupt:
      os.unlink(importdst)
      log.warning("Interrupted!")

  def game_import(self, args):
    if not os.path.isfile(args['importfile']):
      log.error("Import list {} doesn't exist!", args['importfile'])
      sys.exit(1)

    if not os.path.isdir(args['directory']):
      log.error("Client directory {} doesn't exist!", args['directory'])
      sys.exit(1)

    importfile = os.path.sep.join([args['directory'], starcache.IMPORTFILE])
    importedfile = os.path.sep.join([args['directory'], starcache.IMPORTEDFILE])
    cachefile = os.path.sep.join([args['directory'], starcache.CACHEFILE])
    recentfile = os.path.sep.join([args['directory'], starcache.RECENTFILE]) 
    backup = cachefile + '.backup' if os.path.isfile(cachefile) else None
    if args['clean']:
      backup = None
    if backup is not None and os.path.isfile(backup):
      log.error("Previous backup file {} exists!", backup)
      sys.exit(1)

    # Backup VisitedStarsCache.dat.
    if backup is not None:
      try:
        log.debug("Backing up {}", cachefile)
        shutil.move(cachefile, backup)
      except IOError:
        log.error("Failed to back up {} as {}!", cachefile, backup)
        sys.exit(1)

    if args['clean']:
      if os.path.isfile(cachefile):
        log.info("Removing existing {} because --clean was used", cachefile)
        os.unlink(cachefile)

    num_imports = 0
    num_cached = 0
    try:
      with open(args['importfile'], 'r') as f:
        num_imports = len([n for n in f])
    except IOError:
      log.error("Failed to validate {}", importfile)

    # Create ImportStars.txt.
    if num_imports:
      self.client_import(args['importfile'], importfile, importedfile, recentfile)
    else:
      log.warning("Skipping {}", args['importfile'])

    # Delete old ImportStars.text.imported so it can be overridden.
    if os.path.isfile(importedfile):
      log.info("Cleaning up {}", importedfile)
      os.unlink(importedfile)

    # Extract VisitedStarsCache.dat.
    if os.path.isfile(cachefile):
      try:
        log.info("Copying {} to {}", cachefile, args['cachefile'])
        shutil.copyfile(cachefile, args['cachefile'])
      except IOError:
        log.error("Failed to copy {} to {}", cachefile, args['cachefile'])
      if args['clean']:
        os.unlink(cachefile)

    # Restore backed up VisitedStarsCache.dat.
    if backup is not None:
      try:
        log.debug("Restoring {}", cachefile)
        shutil.move(backup, cachefile)
      except IOError:
        log.error("Failed to restore {} from {}!", cachefile, backup)
        sys.exit(1)

    try:
      num_cached = len(list(starcache.parse_visited_stars_cache(args['cachefile'])))
    except IOError:
      log.error("Failed to validate {}", args['cachefile'])

    if num_cached < num_imports:
      log.warning("Names in: {}; IDs out: {}", num_imports, num_cached)
    else:
      log.info("Mapped {} name(s)", num_cached)

  def run_import(self, envdata, args):
    return self.game_import({
      'cachefile': args.cachefile,
      'clean': args.clean,
      'directory': args.directory,
      'importfile': args.importfile
    })

  def run_read(self, envdata, args):
    id64list = []
    batch_size = 512
    for id64 in starcache.parse_visited_stars_cache(args.readfile):
      id64list.append(id64)
      if len(id64list) >= batch_size:
        self.batch_read(envdata, id64list)
        id64list = []
    if len(id64list):
      self.batch_read(envdata, id64list)

  def run_write(self, envdata, args):
    filters = filtering.entry_separator.join(args.filters) if len(args.filters) else None
    if args.importfile:
      with open(args.importfile, 'r') as f:
        iterator = envdata.find_systems_by_name([n.strip() for n in f], filters)
    else:
        iterator = envdata.find_all_systems(filters)
    starcache.write_visited_stars_cache(args.writefile, iterator, self.args.recent)

if __name__ == '__main__':
  env.start()
  a = Application(env.local_args, False)
  a.run()
