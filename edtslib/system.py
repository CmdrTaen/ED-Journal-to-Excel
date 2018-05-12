from . import env
from . import pgnames
from . import util
from .system_internal import System, HASystem, KnownSystem, PGSystem, PGSystemPrototype
from .system_internal import calculate_from_id64, calculate_id64, mask_id64_as_system, mask_id64_as_body, mask_id64_as_boxel, combine_to_id64


def from_id64(id64, allow_ha = True, allow_known = True):
  if util.is_str(id64):
    id64 = int(id64, 16)
  if allow_known:
    with env.use() as data:
      ks = data.get_system_by_id64(mask_id64_as_system(id64))
      if ks is not None:
        return ks
  coords, cube_width, n2, _ = calculate_from_id64(id64)
  # Get a system prototype to steal its name
  sys_proto = pgnames.get_system(coords, cube_width, allow_ha)
  name = sys_proto.name + str(n2)
  x, y, z = sys_proto.position
  return PGSystem(x, y, z, name, sector=sys_proto.sector, uncertainty=cube_width/2.0)


def from_name(name, allow_ha = True, allow_known = True, allow_id64data = True):
  if allow_known:
    with env.use() as data:
      known_sys = data.get_system(name)
      if known_sys is not None:
        return known_sys
  pg_sys = pgnames.get_system(name, allow_ha=allow_ha)
  if pg_sys is not None:
    return pg_sys
  if allow_id64data:
    # TODO: Import unknown-ID64s to the database and query via there instead?
    from . import id64data
    id64 = id64data.get_id64(name, None)
    if id64 is not None:
      coords, cube_width, _, _ = calculate_from_id64(id64)
      return HASystem(coords.x, coords.y, coords.z, name, id64, cube_width / 2)