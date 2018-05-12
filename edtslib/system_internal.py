import math
import struct

from .pgnames import get_system as pg_get_system
from .pgnames import get_system_fragments as pg_get_system_fragments
from .pgnames import get_sector as pg_get_sector
from .pgnames import get_boxel_origin as pg_get_boxel_origin
from . import sector
from . import util
from . import vector3

class System(object):
  def __init__(self, x, y, z, name = None, id64 = None, uncertainty = 0.0):
    self._position = vector3.Vector3(float(x), float(y), float(z))
    self._name = name
    self._id = None
    self._id64 = id64
    self._uncertainty = uncertainty
    self.uses_sc = False
    self._hash = u"{}/{},{},{}".format(self.name, self.position.x, self.position.y, self.position.z).__hash__()

  @property
  def system_name(self):
    return self.name

  @property
  def position(self):
    return self._position

  @property
  def name(self):
    return self._name

  @property
  def pg_name(self):
    if self.id64 is not None:
      coords, cube_width, n2, _ = calculate_from_id64(self.id64)
      sys_proto = pg_get_system(coords, cube_width, allow_ha=False)
      return sys_proto.name + str(n2)
    else:
      return None

  @property
  def id(self):
    return self._id

  @property
  def id64(self):
    if self._id64 is None:
      if self.name is not None:
        m = pg_get_system_fragments(self.name)
        if m is not None:
          self._id64 = calculate_id64(self.position, m['MCode'], m['N2'])
    return self._id64

  @property
  def sector(self):
    return pg_get_sector(self.position)

  @property
  def pg_sector(self):
    return pg_get_sector(self.position, allow_ha=False)

  @property
  def needs_permit(self):
    return self.sector.needs_permit

  @property
  def needs_system_permit(self):
    return False

  @property
  def uncertainty(self):
    return self._uncertainty

  @property
  def uncertainty3d(self):
    return math.sqrt((self.uncertainty**2) * 3)

  def to_string(self, use_long = False):
    if use_long:
      return u"{0} ({1:.2f}, {2:.2f}, {3:.2f})".format(self.name, self.position.x, self.position.y, self.position.z)
    else:
      return u"{0}".format(self.name)

  def __str__(self):
    return self.to_string()

  def __repr__(self):
    return u"System({})".format(self.name)

  def distance_to(self, other):
    other = util.get_as_position(other)
    if other is not None:
      return (self.position - other).length
    else:
      raise ValueError("distance_to argument must be position-like object")

  def __eq__(self, other):
    if isinstance(other, System):
      return (self.name == other.name and self.position == other.position)
    else:
      return NotImplemented

  def pretty_id64(self, fmt = 'INT'):
    if self.id64 is None:
      return "MISSING ID64"
    if fmt == 'VSC':
      return ' '.join('{0:02X}'.format(b) for b in bytearray(struct.pack('<Q', self.id64)))
    else:
      return ("{0:016X}" if fmt == 'HEX' else "{0:d}").format(self.id64)

  def __hash__(self):
    return self._hash


class PGSystemPrototype(System):
  def __init__(self, x, y, z, name, sector, uncertainty):
    super(PGSystemPrototype, self).__init__(x, y, z, name, uncertainty=uncertainty)
    self._sector = sector

  @property
  def sector(self):
    return self._sector

  def __repr__(self):
    return u"PGSystemPrototype({})".format(self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y, self.position.z))

  def __hash__(self):
    return super(PGSystemPrototype, self).__hash__()


class PGSystem(PGSystemPrototype):
  def __init__(self, x, y, z, name, sector, uncertainty):
    super(PGSystem, self).__init__(x, y, z, name, sector, uncertainty)

  def __repr__(self):
    return u"PGSystem({})".format(self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y, self.position.z))

  def __hash__(self):
    return super(PGSystem, self).__hash__()


class HASystem(System):
  def __init__(self, x, y, z, name, id64, uncertainty):
    super(HASystem, self).__init__(x, y, z, name, id64, uncertainty)

  def __repr__(self):
    return u"HASystem({})".format(self.name if self.name is not None else '{},{},{}'.format(self.position.x, self.position.y, self.position.z))

  def __hash__(self):
    return super(HASystem, self).__hash__()


class KnownSystem(HASystem):
  def __init__(self, obj):
    super(KnownSystem, self).__init__(float(obj['x']), float(obj['y']), float(obj['z']), obj['name'], obj['id64'], 0.0)
    self._id = obj['id'] if 'id' in obj else None
    self._needs_permit = obj['needs_permit'] if 'needs_permit' in obj else None
    self._allegiance = obj['allegiance'] if 'allegiance' in obj else None
    self._arrival_star_class = obj['arrival_star_class'] if 'arrival_star_class' in obj else None

  @property
  def needs_permit(self):
    return (self.needs_system_permit or self.sector.needs_permit)

  @property
  def needs_system_permit(self):
    return self._needs_permit

  @property
  def allegiance(self):
    return self._allegiance

  @property
  def arrival_star_class(self):
    return self._arrival_star_class

  def __repr__(self):
    return u"KnownSystem({0})".format(self.name)

  def __eq__(self, other):
    if isinstance(other, KnownSystem):
      return ((self.id is None or other.id is None or self.id == other.id) and self.name == other.name and self.position == other.position)
    elif isinstance(other, System):
      return super(KnownSystem, self).__eq__(other)
    else:
      return NotImplemented

  def __hash__(self):
    return super(KnownSystem, self).__hash__()

    
#
# System ID calculations
#

def mask_id64_as_system(i):
  result = i
  if util.is_str(result):
    result = int(result, 16)
  result &= (2**55) - 1
  return result


def mask_id64_as_body(i):
  result = i
  if util.is_str(result):
    result = int(result, 16)
  result >>= 55
  result &= (2**9)-1
  return result


def mask_id64_as_boxel(i):
  result = i
  if util.is_str(result):
    result = int(result, 16)
  numbits = 44 - 3*(result & 2**3-1) # 44 - 3*mc
  result &= (2**numbits) - 1
  return result


def combine_to_id64(system, body):
  return (system & (2**55-1)) + ((body & (2**9-1)) << 55)


def calculate_from_id64(i):
  # If i is a string, assume hex
  if util.is_str(i):
    i = int(i, 16)
  # Calculate the shifts we need to do to get the individual fields out
  len_used = 0
  i, mc       = util.unpack_and_shift(i, 3);    len_used += 3    # mc = 0-7 for a-h
  i, boxel_z  = util.unpack_and_shift(i, 7-mc); len_used += 7-mc
  i, sector_z = util.unpack_and_shift(i, 7);    len_used += 7
  i, boxel_y  = util.unpack_and_shift(i, 7-mc); len_used += 7-mc
  i, sector_y = util.unpack_and_shift(i, 6);    len_used += 6
  i, boxel_x  = util.unpack_and_shift(i, 7-mc); len_used += 7-mc
  i, sector_x = util.unpack_and_shift(i, 7);    len_used += 7
  i, n2       = util.unpack_and_shift(i, 55-len_used)
  i, body_id  = util.unpack_and_shift(i, 9)
  # Multiply each X/Y/Z value by the cube width to get actual coords
  boxel_size = 10 * (2**mc)
  coord_x = (sector_x * sector.sector_size) + (boxel_x * boxel_size) + (boxel_size / 2)
  coord_y = (sector_y * sector.sector_size) + (boxel_y * boxel_size) + (boxel_size / 2)
  coord_z = (sector_z * sector.sector_size) + (boxel_z * boxel_size) + (boxel_size / 2)
  coords_internal = vector3.Vector3(coord_x, coord_y, coord_z)
  # Shift the coords to be the origin we know and love
  coords = coords_internal + sector.internal_origin_offset
  return (coords, boxel_size, n2, body_id)


def calculate_id64(pos, mcode, n2, body = 0):
  # Get the data we need to start with (mc as 0-7, cube width, boxel X/Y/Z coords)
  mc = ord(sector.get_mcode(mcode)) - ord('a')
  cube_width = sector.get_mcode_cube_width(mcode)
  boxel_coords = (pg_get_boxel_origin(pos, mcode) - sector.internal_origin_offset) / cube_width
  # Populate each field, shifting as required
  output = util.pack_and_shift(0, int(body), 9)
  output = util.pack_and_shift(output, int(n2), 11+mc*3)
  output = util.pack_and_shift(output, int(boxel_coords.x), 14-mc)
  output = util.pack_and_shift(output, int(boxel_coords.y), 13-mc)
  output = util.pack_and_shift(output, int(boxel_coords.z), 14-mc)
  output = util.pack_and_shift(output, mc, 3)
  return output

