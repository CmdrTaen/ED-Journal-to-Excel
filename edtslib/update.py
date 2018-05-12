#!/usr/bin/env python

from __future__ import print_function, division
from time import time
import argparse
import gc
import json
import os
import shutil
import re
import sys
import tempfile

from . import db_sqlite3 as db
from . import defs
from . import env
from . import util

log = util.get_logger("update")

class DownloadOnly(object):
  def ignore(self, many):
    for _ in many:
      continue

  populate_table_systems = ignore
  populate_table_stations = ignore
  populate_table_coriolis_fsds = ignore
  update_table_systems = ignore
  def close(self): pass

edsm_systems_url  = "https://www.edsm.net/dump/systemsWithCoordinates.json"
eddb_systems_url  = "https://eddb.io/archive/v5/systems_populated.jsonl"
eddb_stations_url = "https://eddb.io/archive/v5/stations.jsonl"
coriolis_fsds_url = "https://raw.githubusercontent.com/cmmcleod/coriolis-data/master/modules/standard/frame_shift_drive.json"

edsm_systems_local_path  = "data/systemsWithCoordinates.json"
eddb_systems_local_path  = "data/systems_populated.jsonl"
eddb_stations_local_path = "data/stations.jsonl"
coriolis_fsds_local_path = "data/frame_shift_drive.json"

_re_json_line = re.compile(r'^\s*(\{.*\})[\s,]*$')


def cleanup_local(f, scratch):
  if f is not None and not f.closed:
    try:
      f.close()
    except:
      log.error("Error closing temporary file{}", ' {}'.format(scratch) if scratch is not None else '')
  if scratch is not None:
    try:
      os.unlink(scratch)
    except:
      log.error("Error cleaning up temporary file {}", scratch)


class Application(object):

  def __init__(self, arg, hosted, state = {}):
    ap = argparse.ArgumentParser(description = 'Update local database', parents = [env.arg_parser], prog = "update")
    ap.add_argument_group("Processing options")
    bex = ap.add_mutually_exclusive_group()
    bex.add_argument('-b', '--batch', dest='batch', action='store_true', default=True, help='Import data in batches')
    bex.add_argument('-n', '--no-batch', dest='batch', action='store_false', help='Import data in one load - this will use massive amounts of RAM and may fail!')
    ap.add_argument('-c', '--copy-local', required=False, action='store_true', help='Keep local copy of downloaded files')
    ap.add_argument('-d', '--download-only', required=False, action='store_true', help='Do not import, just download files - implies --copy-local')
    ap.add_argument('-s', '--batch-size', required=False, type=int, help='Batch size; higher sizes are faster but consume more memory')
    ap.add_argument('-l', '--local', required=False, action='store_true', help='Instead of downloading, update from local files in the data directory')
    ap.add_argument('--print-urls', required=False, action='store_true', help='Do not download anything, just print the URLs which we would fetch from')
    args = ap.parse_args(sys.argv[1:])
    if args.batch or args.batch_size:
      args.batch_size = args.batch_size if args.batch_size is not None else 1024
      if not args.batch_size > 0:
        raise ValueError("Batch size must be a natural number!")
    args.copy_local = args.download_only or args.copy_local
    if args.copy_local and args.local:
      raise ValueError("Invalid use of --local and --{}!", "download-only" if args.download_only else "copy-local")
    self.args = args

  def run(self):
    env.log_versions()
    db.log_versions()

    # Get the relative path to the "edtslib" base directory from the current directory
    relpath = util.get_relative_path(os.getcwd(), os.path.dirname(__file__))

    if self.args.print_urls:
      if self.args.local:
        # Local path hard-specifies "/" so do the same here
        print(relpath + "/" + edsm_systems_local_path)
        print(relpath + "/" + eddb_systems_local_path)
        print(relpath + "/" + eddb_stations_local_path)
        print(relpath + "/" + coriolis_fsds_local_path)
      else:
        print(edsm_systems_url)
        print(eddb_systems_url)
        print(eddb_stations_url)
        print(coriolis_fsds_url)
      return

    if self.args.download_only:
      log.info("Downloading files locally...")
      dbc = DownloadOnly()
    else:
      db_file = os.path.join(defs.default_path, env.global_args.db_file)
      db_dir = os.path.dirname(db_file)

      # If the data directory doesn't exist, make it
      if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)

      # Open then close a temporary file, essentially reserving the name.
      fd, db_tmp_filename = tempfile.mkstemp('.tmp', os.path.basename(db_file), db_dir if db_dir else '.')
      os.close(fd)

      log.info("Initialising database...")
      sys.stdout.flush()
      dbc = db.initialise_db(db_tmp_filename)
      log.info("Done.")

    try:
      # Repoint local paths to use the right relative path
      cur_edsm_systems_local_path  = os.path.join(relpath, edsm_systems_local_path)
      cur_eddb_systems_local_path  = os.path.join(relpath, eddb_systems_local_path)
      cur_eddb_stations_local_path = os.path.join(relpath, eddb_stations_local_path)
      cur_coriolis_fsds_local_path = os.path.join(relpath, coriolis_fsds_local_path)
      # Decide whether to source data from local paths or remote URLs
      edsm_systems_path  = util.path_to_url(cur_edsm_systems_local_path)  if self.args.local else edsm_systems_url
      eddb_systems_path  = util.path_to_url(cur_eddb_systems_local_path)  if self.args.local else eddb_systems_url
      eddb_stations_path = util.path_to_url(cur_eddb_stations_local_path) if self.args.local else eddb_stations_url
      coriolis_fsds_path = util.path_to_url(cur_coriolis_fsds_local_path) if self.args.local else coriolis_fsds_url

      dbc.populate_table_systems(self.import_json_from_url(edsm_systems_path, cur_edsm_systems_local_path, 'EDSM systems', self.args.batch_size, is_url_local=self.args.local))
      dbc.update_table_systems(self.import_json_from_url(eddb_systems_path, cur_eddb_systems_local_path, 'EDDB systems', self.args.batch_size, is_url_local=self.args.local))
      dbc.populate_table_stations(self.import_json_from_url(eddb_stations_path, cur_eddb_stations_local_path, 'EDDB stations', self.args.batch_size, is_url_local=self.args.local))
      dbc.populate_table_coriolis_fsds(self.import_json_from_url(coriolis_fsds_path, cur_coriolis_fsds_local_path, 'Coriolis FSDs', None, is_url_local=self.args.local, key='fsd'))
    except MemoryError:
      log.error("Out of memory!")
      if self.args.batch_size is None:
        log.error("Try the --batch flag for a slower but more memory-efficient method!")
      elif self.args.batch_size > 64:
        log.error("Try --batch-size {0}", self.args.batch_size / 2)
      if not self.args.download_only:
        cleanup_local(None, db_tmp_filename)
      return
    except:
      if not self.args.download_only:
        cleanup_local(None, db_tmp_filename)
      raise

    if not self.args.download_only:
      dbc.close()

      if os.path.isfile(db_file):
        os.unlink(db_file)
      shutil.move(db_tmp_filename, db_file)

    log.info("All done.")

  def import_json_from_url(self, url, filename, description, batch_size, is_url_local = False, key = None):
    if self.args.copy_local:
      try:
        dirname = os.path.dirname(filename)
        fd, scratch = tempfile.mkstemp('.tmp', os.path.basename(filename), dirname if dirname else '.')
        f = os.fdopen(fd, 'wb')
      except:
        log.error("Failed to create a temporary file")
        raise
    try:
      if batch_size is not None:
        log.info("Batch downloading {0} list from {1} ... ", description, url)
        sys.stdout.flush()

        start = int(time())
        done = 0
        failed = 0
        last_elapsed = 0

        batch = []
        encoded = ''
        stream = util.open_url(url, allow_no_ssl=is_url_local)
        if stream is None:
          if self.args.copy_local:
            cleanup_local(f, scratch)
          return
        while True:
          line = util.read_stream_line(stream)
          if not line:
            break
          if self.args.copy_local:
            util.write_stream(f, line)
          if self.args.download_only:
            continue
          m = _re_json_line.match(line)
          if m is None:
            continue
          try:
            obj = json.loads(m.group(1))
          except ValueError:
            log.debug("Line failed JSON parse: {0}", line)
            failed += 1
            continue
          batch.append(obj)
          if len(batch) >= batch_size:
            for obj in batch:
              yield obj
            done += len(batch)
            elapsed = int(time()) - start
            if elapsed - last_elapsed >= 30:
              log.info("Loaded {0} row(s) of {1} data to DB...", done, description)
              last_elapsed = elapsed
            batch = []
          if len(batch) >= batch_size:
            for obj in batch:
              yield obj
            done += len(batch)
            log.info("Loaded {0} row(s) of {1} data to DB...", done, description)
        done += len(batch)
        if not self.args.download_only:
          for obj in batch:
            yield obj
          if failed:
            log.info("Lines failing JSON parse: {0}", failed)
          log.info("Loaded {0} row(s) of {1} data to DB...", done, description)
          log.info("Done.")
      else:
        log.info("Downloading {0} list from {1} ... ", description, url)
        sys.stdout.flush()
        encoded = util.read_from_url(url, allow_no_ssl=is_url_local)
        log.info("Done.")
        if self.args.copy_local:
          log.info("Writing {0} local data...", description)
          util.write_stream(f, encoded)
          log.info("Done.")
        if not self.args.download_only:
          log.info("Loading {0} data...", description)
          sys.stdout.flush()
          obj = json.loads(encoded)
          log.info("Done.")
          log.info("Adding {0} data to DB...", description)
          if key is not None:
            obj = obj[key]
          for o in obj:
            yield o
          log.info("Done.")
      # Force GC collection to try to avoid memory errors
      encoded = None
      obj = None
      batch = None
      gc.collect()
      if self.args.copy_local:
        f.close()
        f = None
        shutil.move(scratch, filename)
    except MemoryError:
      encoded = None
      obj = None
      batch = None
      gc.collect()
      raise
    except:
      if self.args.copy_local:
        cleanup_local(f, scratch)
      raise
