import collections
import json
import re
import sqlite3
import time

from . import defs
from . import env_backend as eb
from . import filtering
from . import util
from . import vector3

log = util.get_logger("db_sqlite3")

schema_version = 8

_find_operators = ['=','LIKE','REGEXP']
# This is nasty, and it may well not be used up in the main code
_bad_char_regex = re.compile(r"[^a-zA-Z0-9'&+:*^%_?.,/#@!=`() -|\[\]]")


def _regexp(expr, item):
  rgx = re.compile(expr)
  return rgx.search(item) is not None


def _list_clause(field, mode, names):
  if mode in [eb.FIND_GLOB, eb.FIND_REGEX]:
    operator = _find_operators[mode]
    return "({})".format(' OR '.join(["{} {} ?".format(field, operator)] * len(names)))
  else:
    return "{} IN ({})".format(field, ','.join(['?'] * len(names)))

def _vec3_angle(x1, y1, z1, x2, y2, z2):
  return vector3.Vector3(x1, y1, z1).angle_to(vector3.Vector3(x2, y2, z2))


def log_versions():
  log.debug("SQLite3: {} / PySQLite: {}", sqlite3.sqlite_version, sqlite3.version)


def open_db(filename = defs.default_db_path, check_version = True):
  conn = sqlite3.connect(filename)
  conn.row_factory = sqlite3.Row
  conn.create_function("REGEXP", 2, _regexp)
  conn.create_function("vec3_angle", 6, _vec3_angle)
 
  if check_version:
    c = conn.cursor()
    c.execute('SELECT db_version FROM edts_info')
    (db_version, ) = c.fetchone()
    if db_version != schema_version:
      log.warning("DB file's schema version {0} does not match the expected version {1}.", db_version, schema_version)
      log.warning("This is likely to cause errors; you may wish to rebuild the database by running update.py")
    log.debug("DB connection opened")
  return SQLite3DBConnection(conn)


def initialise_db(filename = defs.default_db_path):
  dbc = open_db(filename, check_version=False)
  dbc._create_tables()
  return dbc


class SQLite3DBConnection(eb.EnvBackend):
  def __init__(self, conn):
    super(SQLite3DBConnection, self).__init__("db_sqlite3")
    self._conn = conn
    self._is_closed = False

  @property
  def closed(self):
    return self._is_closed

  def close(self):
    self._conn.close()
    self._is_closed = True
    log.debug("DB connection closed")

  def _create_tables(self):
    log.debug("Creating tables...")
    c = self._conn.cursor()
    c.execute('CREATE TABLE edts_info (db_version INTEGER, db_mtime INTEGER)')
    c.execute('INSERT INTO edts_info VALUES (?, ?)', (schema_version, int(time.time())))

    c.execute('CREATE TABLE systems (edsm_id INTEGER NOT NULL UNIQUE, name TEXT COLLATE NOCASE NOT NULL, pos_x REAL NOT NULL, pos_y REAL NOT NULL, pos_z REAL NOT NULL, eddb_id INTEGER, id64 INTEGER, needs_permit BOOLEAN, allegiance TEXT, data TEXT)')
    c.execute('CREATE TABLE stations (eddb_id INTEGER NOT NULL UNIQUE, eddb_system_id INTEGER NOT NULL, name TEXT COLLATE NOCASE NOT NULL, sc_distance INTEGER, station_type TEXT, max_pad_size TEXT, data TEXT)')
    c.execute('CREATE TABLE coriolis_fsds (id TEXT NOT NULL PRIMARY KEY, data TEXT NOT NULL)')

    self._conn.commit()
    log.debug("Done.")

  def _generate_systems(self, systems):
    from . import id64data
    for s in systems:
      pos = vector3.Vector3(float(s['coords']['x']), float(s['coords']['y']), float(s['coords']['z']))
      s_id64 = id64data.get_id64(s['name'], pos)
      yield (int(s['id']), s['name'], pos.x, pos.y, pos.z, s_id64)

  def _generate_systems_update(self, systems):
    for s in systems:
      yield (int(s['id']), bool(s['needs_permit']), s['allegiance'], json.dumps(s), s['edsm_id'])

  def _generate_stations(self, stations):
    for s in stations:
      yield (int(s['id']), int(s['system_id']), s['name'], int(s['distance_to_star']) if s['distance_to_star'] is not None else None, s['type'], s['max_landing_pad_size'], json.dumps(s))

  def _generate_coriolis_fsds(self, fsds):
    for fsd in fsds:
      yield ('{0}{1}'.format(fsd['class'], fsd['rating']), json.dumps(fsd))

  def populate_table_systems(self, many):
    c = self._conn.cursor()
    log.debug("Going for REPLACE INTO systems...")
    c.executemany('REPLACE INTO systems VALUES (?, ?, ?, ?, ?, NULL, ?, NULL, NULL, NULL)', self._generate_systems(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.", c.rowcount)
    log.debug("Going to add indexes to systems for name, pos_x/pos_y/pos_z, edsm_id...")
    c.execute('CREATE INDEX idx_systems_name ON systems (name COLLATE NOCASE)')
    c.execute('CREATE INDEX idx_systems_pos ON systems (pos_x, pos_y, pos_z)')
    c.execute('CREATE INDEX idx_systems_edsm_id ON systems (edsm_id)')
    c.execute('CREATE INDEX idx_systems_id64 ON systems (id64)')
    self._conn.commit()
    log.debug("Indexes added.")


  def update_table_systems(self, many):
    c = self._conn.cursor()
    log.debug("Going for UPDATE systems...")
    c.executemany('UPDATE systems SET eddb_id=?, needs_permit=?, allegiance=?, data=? WHERE edsm_id=?', self._generate_systems_update(many))
    self._conn.commit()
    log.debug("Done, {} rows affected.", c.rowcount)
    log.debug("Going to add indexes to systems for eddb_id...")
    c.execute('CREATE INDEX idx_systems_eddb_id ON systems (eddb_id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def populate_table_stations(self, many):
    c = self._conn.cursor()
    log.debug("Going for REPLACE INTO stations...")
    c.executemany('REPLACE INTO stations VALUES (?, ?, ?, ?, ?, ?, ?)', self._generate_stations(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.", c.rowcount)
    log.debug("Going to add indexes to stations for name, eddb_system_id...")
    c.execute('CREATE INDEX idx_stations_name ON stations (name COLLATE NOCASE)')
    c.execute('CREATE INDEX idx_stations_sysid ON stations (eddb_system_id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def populate_table_coriolis_fsds(self, many):
    log.debug("Going for REPLACE INTO coriolis_fsds...")
    c = self._conn.cursor()
    c.executemany('REPLACE INTO coriolis_fsds VALUES (?, ?)', self._generate_coriolis_fsds(many))
    self._conn.commit()
    log.debug("Done, {} rows inserted.", c.rowcount)
    log.debug("Going to add indexes to coriolis_fsds for id...")
    c.execute('CREATE INDEX idx_coriolis_fsds_id ON coriolis_fsds (id)')
    self._conn.commit()
    log.debug("Indexes added.")

  def retrieve_fsd_list(self):
    c = self._conn.cursor()
    cmd = 'SELECT id, data FROM coriolis_fsds'
    log.debug("Executing: {}", cmd)
    c.execute(cmd)
    results = c.fetchall()
    log.debug("Done.")
    return dict([(k, json.loads(v)) for (k, v) in results])

  def get_system_by_id64(self, id64, fallback_name = None):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE id64 = ?'
    data = (id64, )
    if fallback_name:
      cmd += ' OR name = ?'
      data = (id64, fallback_name)
    log.debug("Executing: {}; id64 = {}, name = {}", cmd, id64, fallback_name)
    c.execute(cmd, data)
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return _process_system_result(result)
    else:
      return None

  def get_system_by_name(self, name):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE name = ?'
    log.debug("Executing: {}; name = {}", cmd, name)
    c.execute(cmd, (name, ))
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return _process_system_result(result)
    else:
      return None

  def get_systems_by_name(self, names):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, id64, data FROM systems WHERE name IN ({})'.format(','.join(['?'] * len(names)))
    log.debug("Executing: {}; names = {}", cmd, names)
    c.execute(cmd, names)
    result = c.fetchall()
    log.debug("Done.")
    if result is not None:
      return [_process_system_result(r) for r in result]
    else:
      return None

  def get_station_by_names(self, sysname, stnname):
    c = self._conn.cursor()
    cmd = 'SELECT sy.name AS name, sy.pos_x AS pos_x, sy.pos_y AS pos_y, sy.pos_z AS pos_z, sy.id64 AS id64, sy.data AS data, st.data AS stndata FROM systems sy, stations st WHERE sy.name = ? AND st.name = ? AND sy.eddb_id = st.eddb_system_id'
    log.debug("Executing: {}; sysname = {}, stnname = {}", cmd, sysname, stnname)
    c.execute(cmd, (sysname, stnname))
    result = c.fetchone()
    log.debug("Done.")
    if result is not None:
      return (_process_system_result(result), json.loads(result['stndata']))
    else:
      return (None, None)

  def get_stations_by_names(self, names):
    c = self._conn.cursor()
    extra_cmd = ' OR '.join(['sy.name = ? AND st.name = ?'] * len(names))
    cmd = 'SELECT sy.name AS name, sy.pos_x AS pos_x, sy.pos_y AS pos_y, sy.pos_z AS pos_z, sy.id64 AS id64, sy.data AS data, st.data AS stndata FROM systems sy, stations st WHERE sy.eddb_id = st.eddb_system_id AND ({})'.format(extra_cmd)
    log.debug("Executing: {}; names = {}", cmd, names)
    c.execute(cmd, [n for sublist in names for n in sublist])
    result = c.fetchall()
    log.debug("Done.")
    if result is not None:
      return [(_process_system_result(r), json.loads(r['stndata'])) for r in result]
    else:
      return (None, None)


  def find_stations_by_system_id(self, args, filters = None):
    sysids = args if isinstance(args, collections.Iterable) else [args]
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['stations'],
      ['stations.eddb_system_id', 'stations.data'],
      ['eddb_system_id IN ({})'.format(','.join(['?'] * len(sysids)))],
      [],
      sysids,
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    results = c.fetchall()
    log.debug("Done, {} results.", len(results))
    return [{ k: v for d in [{ 'eddb_system_id': r[0] }, json.loads(r[1])] for k, v in d.items()} for r in results]

  def find_systems_by_aabb(self, min_x, min_y, min_z, max_x, max_y, max_z, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      ['? <= systems.pos_x', 'systems.pos_x < ?', '? <= systems.pos_y', 'systems.pos_y < ?', '? <= systems.pos_z', 'systems.pos_z < ?'],
      [],
      [min_x, max_x, min_y, max_y, min_z, max_z],
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    results = c.fetchall()
    log.debug("Done, {} results.", len(results))
    return [_process_system_result(r) for r in results]
    
  def find_systems_by_name(self, namelist, mode = eb.FIND_EXACT, filters = None):
    # return self.find_systems_by_name_safe(namelist, mode, filters)
    return self.find_systems_by_name_unsafe(namelist, mode, filters)

  def find_systems_by_id64(self, id64list, filters = None):
    return self.find_systems_by_id64_safe(id64list, filters)

  def find_stations_by_name(self, name, mode = eb.FIND_EXACT, filters = None):
    # return self.find_stations_by_name_safe(name, mode, filters)
    return self.find_stations_by_name_unsafe(name, mode, filters)

  def find_systems_by_name_safe(self, namelist, mode = eb.FIND_EXACT, filters = None):
    names = util.flatten(namelist)
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      names = [name.replace('*','%').replace('?','_') for name in names]
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      [_list_clause('systems.name', mode, names)],
      [],
      names,
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  def find_stations_by_name_safe(self, name, mode = eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      ['stations.name {} ?'.format(_find_operators[mode])],
      [],
      [name],
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  def find_systems_by_id64_safe(self, id64list, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      ["systems.id64 IN ({})".format(','.join(['?'] * len(id64list)))],
      [],
      id64list,
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  # WARNING: VERY UNSAFE, USE WITH CARE
  # These methods exist due to a bug in the Python sqlite3 module
  # Using bound parameters as the safe versions do results in indexes being ignored
  # This significantly slows down searches (~500x at time of writing) due to doing full table scans
  # So, these methods are fast but vulnerable to SQL injection due to use of string literals
  # This will hopefully be unnecessary in Python 2.7.11+ / 3.6.0+ if porting of a newer pysqlite2 version is completed
  def find_systems_by_name_unsafe(self, namelist, mode=eb.FIND_EXACT, filters = None):
    names = util.flatten(namelist)
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      names = map(lambda name: name.replace('*','%').replace('?','_'), names)
    names = map(lambda name: _bad_char_regex.sub("", name), names)
    names = map(lambda name: name.replace("'", r"''"), names)
    names = list(names)
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      [_list_clause('systems.name', mode, names)],
      [],
      names,
      filters)
    log.debug("Executing (U): {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  def find_stations_by_name_unsafe(self, name, mode=eb.FIND_EXACT, filters = None):
    if mode == eb.FIND_GLOB and _find_operators[mode] == 'LIKE':
      name = name.replace('*','%').replace('?','_')
    name = _bad_char_regex.sub("", name)
    name = name.replace("'", r"''")
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      ["stations.name {} '{}'".format(_find_operators[mode], name)],
      [],
      [],
      filters)
    c = self._conn.cursor()
    log.debug("Executing (U): {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  # Slow as sin; avoid if at all possible
  def find_all_systems(self, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data'],
      [],
      [],
      [],
      filters)
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()

  # Slow as sin; avoid if at all possible
  def find_all_stations(self, filters = None):
    c = self._conn.cursor()
    cmd, params = _construct_query(
      ['systems', 'stations'],
      ['systems.name AS name', 'systems.pos_x AS pos_x', 'systems.pos_y AS pos_y', 'systems.pos_z AS pos_z', 'systems.id64 AS id64', 'systems.data AS data', 'stations.data AS stndata'],
      [],
      [],
      [],
      filters) 
    log.debug("Executing: {}; params = {}", cmd, params)
    c.execute(cmd, params)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield (_process_system_result(result), json.loads(result['stndata']))
      result = c.fetchone()

  def get_populated_systems(self):
    c = self._conn.cursor()
    cmd = 'SELECT name, pos_x, pos_y, pos_z, data FROM systems WHERE allegiance IS NOT NULL'
    log.debug("Executing: {}", cmd)
    c.execute(cmd)
    result = c.fetchone()
    log.debug("Done.")
    while result is not None:
      yield _process_system_result(result)
      result = c.fetchone()


def _process_system_result(result):
  if 'data' in result.keys() and result['data'] is not None:
    data = json.loads(result['data'])
    data['id64'] = result['id64']
    return data
  else:
    return {'name': result['name'], 'x': result['pos_x'], 'y': result['pos_y'], 'z': result['pos_z'], 'id64': result['id64']}

def _construct_query(qtables, select, qfilter, select_params = None, filter_params = None, filters = None):
  select_params = select_params or []
  filter_params = filter_params or []
  tables = qtables
  qmodifier = []
  qmodifier_params = []
  # Apply any user-defined filters
  if filters:
    fsql = filtering.generate_sql(filters)
    tables = set(qtables + fsql['tables'])
    select = select + fsql['select'][0]
    qfilter = qfilter + fsql['filter'][0]
    select_params += fsql['select'][1]
    filter_params += fsql['filter'][1]
    group = fsql['group'][0]
    group_params = fsql['group'][1]
    # Hack, since we can't really know this before here :(
    if 'stations' in tables and 'systems' in tables:
      qfilter.append("systems.eddb_id=stations.eddb_system_id")
      # More hack: if we weren't originally joining on stations, group results by system
      if 'stations' not in qtables:
        group.append('systems.eddb_id')
    # If we have any groups/ordering/limiting, set it up
    if any(group):
      qmodifier.append('GROUP BY {}'.format(', '.join(group)))
      qmodifier_params += group_params
    if any(fsql['order'][0]):
      qmodifier.append('ORDER BY {}'.format(', '.join(fsql['order'][0])))
      qmodifier_params += fsql['order'][1]
    if fsql['limit']:
      qmodifier.append('LIMIT {}'.format(fsql['limit']))
  else:
    # Still need to check this
    if 'stations' in tables and 'systems' in tables:
      qfilter.append("systems.eddb_id=stations.eddb_system_id")

  q1 = 'SELECT {} FROM {}'.format(','.join(select), ','.join(tables))
  q2 = 'WHERE {}'.format(' AND '.join(qfilter)) if any(qfilter) else ''
  q3 = ' '.join(qmodifier)
  query = '{} {} {}'.format(q1, q2, q3)
  params = select_params + filter_params + qmodifier_params
  return (query, params)
