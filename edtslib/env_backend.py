
FIND_EXACT = 0
FIND_GLOB = 1
FIND_REGEX = 2

class EnvBackend(object):
  # SystemResult = {"name": str, "x": float, "y": float, "z": float, "id64": int or None, ...}
  # StationResult = {"name": str, "type": str, "has_refuel": bool, "is_planetary": bool, "max_landing_pad_size": str, "distance_to_star": float, ...}
  # All methods returning list-like objects may instead return generators or other iterators

  def __init__(self, backend_name):
    self.backend_name = backend_name

  def retrieve_fsd_list(self):
    # return {"fsd_class": fsd_object}
    raise NotImplementedError("Invalid use of base EnvBackend retrieve_fsd_list method")

  def get_system_by_id64(self, id64, fallback_name = None):
    # return SystemResult
    raise NotImplementedError("Invalid use of base EnvBackend get_system_by_id64 method")

  def get_system_by_name(self, name):
    # return SystemResult
    raise NotImplementedError("Invalid use of base EnvBackend get_system_by_name method")

  def get_systems_by_name(self, names):
    # return [SystemResult, ...]
    raise NotImplementedError("Invalid use of base EnvBackend get_systems_by_name method")

  def get_station_by_names(self, sysname, stnname):
    # return (SystemResult, StationResult)
    raise NotImplementedError("Invalid use of base EnvBackend get_station_by_names method")

  def get_stations_by_names(self, names):
    # return [(SystemResult, StationResult), ...]
    raise NotImplementedError("Invalid use of base EnvBackend get_stations_by_names method")

  def find_stations_by_system_id(self, args, filters = None):
    # return [StationResult + {"eddb_station_id": int}, ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_stations_by_system_id method")

  def find_systems_by_aabb(self, min_x, min_y, min_z, max_x, max_y, max_z, filters = None):
    # return [SystemResult, ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_systems_by_aabb method")

  def find_systems_by_name(self, namelist, mode = FIND_EXACT, filters = None):
    # return [SystemResult, ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_systems_by_name method")

  def find_systems_by_id64(self, id64list, filters = None):
    # return [SystemResult, ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_systems_by_id64 method")

  def find_stations_by_name(self, name, mode = FIND_EXACT, filters = None):
    # return [(SystemResult, StationResult), ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_stations_by_name method")

  def find_all_systems(self, filters = None):
    # return [SystemResult, ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_all_systems method")

  def find_all_stations(self, filters = None):
    # return [(SystemResult, StationResult), ...]
    raise NotImplementedError("Invalid use of base EnvBackend find_all_stations method")
