import collections
import math
import re
import sys

from . import station
from . import util

log = util.get_logger("filter")

default_direction_angle = 15.0

value_literalarg = '?'
entry_separator = ';'
# Split on ',' but keep anything inside '[1,2,3]' blocks as single elements
entry_subelement_re = re.compile(r'(?:([^,\[]+?|\[[^\]]+?\])(?:,|$))+?')
entry_kvseparator_re = re.compile(r'(=|!=|<>|<=|>=|<|>)')
# Note: '!=' allows null/None, '<>' does not


class AnyType(object):
  def __str__(self):
    return "Any"
  def __repr__(self):
    return "Any"
Any = AnyType()

class PosArgsType(object):
  def __str__(self):
    return "PosArgs"
  def __repr__(self):
    return "PosArgs"
PosArgs = PosArgsType()

class PadSize(object):
  values = ['S','M','L']
  def __init__(self, value):
    if util.is_str(value):
      value = value.upper()
    self.value = value if value in PadSize.values else None
  def __str__(self):
    return self.value
  def __repr__(self):
    return self.value
  def __cmp__(self, rhs):
    if isinstance(rhs, PadSize):
      rhs = rhs.value
    if rhs is Any:
      return 0
    if rhs is None:
      return sys.maxsize
    if not rhs in PadSize.values:
      raise ValueError('tried to compare pad size with an invalid value')
    return (PadSize.values.index(self.value) - PadSize.values.index(rhs))
  # Python 3.x doesn't like __cmp__
  def __lt__(self, rhs): return (self.__cmp__(rhs) < 0)
  def __le__(self, rhs): return (self.__cmp__(rhs) <= 0)
  def __gt__(self, rhs): return (self.__cmp__(rhs) > 0)
  def __ge__(self, rhs): return (self.__cmp__(rhs) >= 0)
  def __eq__(self, rhs): return (self.__cmp__(rhs) == 0)
  def __ne__(self, rhs): return (self.__cmp__(rhs) != 0)

class Operator(object):
  def __init__(self, op, value):
    self.value = value
    self.operator = op
  def __str__(self):
    return "{} {}".format(self.operator, self.value)
  def __repr__(self):
    return "{} {}".format(self.operator, self.value)
  def matches(self, rhs):
    if self.operator == '=':
      if self.value is Any or rhs is Any:
        return (self.value is not None and rhs is not None)
      else:
        return (rhs != self.value)
    elif self.operator == '!=':
      if self.value is Any or rhs is Any:
        return (self.value is None or rhs is None)
      else:
        return (rhs != self.value)
    elif self.operator == '<>':
      if self.value is Any or rhs is Any:
        return (self.value is None or rhs is None)
      else:
        return (rhs != self.value and rhs is not None)
    elif self.operator == '<':
      return (rhs < self.value)
    elif self.operator == '<=':
      return (rhs <= self.value)
    elif self.operator == '>=':
      return (rhs >= self.value)
    elif self.operator == '>':
      return (rhs > self.value)
    else:
      raise ValueError("Operator '{}' is invalid".format(self.operator))

_assumed_operators = {int: '<', float: '<'}


def _get_valid_ops(fn):
  if isinstance(fn, dict) and 'fn' in fn:
    return _get_valid_ops(fn['fn'])
  if fn is int or fn is float or fn is PadSize:
    return ['=','!=','<','>','<=','>=']
  if isinstance(fn, dict):
    return ['=']
  else:
    return ['=','!=','<>']

def _get_valid_conversion(fndict, idx, subidx = None):
  if idx in fndict:
    if isinstance(fndict[idx], dict) and 'fn' in fndict[idx]:
      return fndict[idx]['fn']
    else:
      return fndict[idx]
  if idx is None:
    if subidx is not None and subidx in fndict:
      return fndict[subidx]
    elif PosArgs in fndict:
      return fndict[PosArgs]
  return None

_conversions = {
  'sc_distance': {
                   'max': None,
                   'special': [Any],
                   'fn': int
                 },
  'pad':         {
                   'max': 1,
                   'special': [Any, None],
                   'fn': PadSize
                 },
  'close_to':    {
                   'max': None,
                   'special': [],
                   'fn':
                   {
                     PosArgs: 'system',
                     'distance':  {'max': None, 'special': [], 'fn': float},
                     'direction': {'max': None, 'special': [], 'fn': 'system'},
                     'angle':     {'max': None, 'special': [], 'fn': float}
                   }
                 },
  'allegiance':  {
                   'max': 1,
                   'special': [Any, None],
                   'fn': str
                 },
  'limit':       {
                   'max': 1,
                   'special': [],
                   'fn': int
                 },
}


def _global_conv(val, specials = None):
  specials = specials or []
  if isinstance(val, Operator):
    return (Operator(value=_global_conv(val.value, specials), op=val.operator), False)

  if val.lower() == "any" and Any in specials:
    return (Any, False)
  elif val.lower() == "none" and None in specials:
    return (None, False)
  else:
    return (val, True)


def parse(filter_string, *args, **kwargs):
  extra_converters = kwargs.get('extra_converters', {})
  entries = filter_string.split(entry_separator)
  # This needs to be ordered so that literal args ('?') are hit in the correct order
  output = collections.OrderedDict()
  # For each separate filter entry...
  for entry in entries:
    ksv = entry_kvseparator_re.split(entry, 1)
    key = ksv[0].strip()
    if key not in _conversions:
      raise KeyError("Unexpected filter key provided: {0}".format(key))
    ksvlist = entry_subelement_re.findall(ksv[2].strip())
    # Do we have sub-entries, or just a simple key=value ?
    value = collections.OrderedDict()
    # For each sub-entry...
    for e in ksvlist:
      eksv = [es.strip() for es in entry_kvseparator_re.split(e, 1)]
      # Is this sub-part a subkey=value?
      if len(eksv) > 1:
        if eksv[0] not in value:
          value[eksv[0]] = []
        value[eksv[0]].append(Operator(value=eksv[2], op=eksv[1]))
      else:
        # If not, give it a position-based index
        if PosArgs not in value:
          value[PosArgs] = []
        value[PosArgs].append(Operator(value=eksv[0], op=ksv[1]))
    # Set the value and move on
    if key not in output:
      output[key] = []
    output[key].append(value)

  literalarg_count = 0
  # For each result
  for k in output.keys():
    # Do we know about it?
    if k in _conversions:
      if _conversions[k]['max'] not in [None, 1] and len(output[k]) > _conversions[k]['max']:
        raise KeyError("Filter key {} provided more than its maximum {} times".format(k, _conversions[k]['max']))
      # Is it a complicated one, or a simple key=value?
      if isinstance(_conversions[k]['fn'], dict):
        # For each present subkey, check if we know about it
        outlist = output[k]
        # For each subkey...
        for outentry in outlist:
          # For each named entry in that subkey (and None for positional args)...
          for ek in outentry:
            # For each instance of that named entry...
            for i in range(0, len(outentry[ek])):
              ev = outentry[ek][i]
              # Check we have a valid conversion for the provided name
              conv = _get_valid_conversion(_conversions[k]['fn'], ek, i)
              if not conv:
                raise KeyError("Unexpected filter subkey provided: {0}".format(ek))
              # Check the provided operator is valid in this scenario
              if ev.operator not in _get_valid_ops(conv):
                raise KeyError("Invalid operator provided for filter subkey '{}/{}'".format(k, ek))
              # Do the conversions
              specials = _conversions[k]['fn'][ek]['special'] if (ek in _conversions[k]['fn'] and isinstance(_conversions[k]['fn'][ek], dict)) else []
              ev.value, continue_conv = _global_conv(ev.value, specials)
              if continue_conv:
                if ev.value == value_literalarg:
                  if literalarg_count >= len(args):
                    raise ValueError("Query included more literal args ('{}') than argument objects provided to parse function".format(value_literalarg))
                  ev.value = args[literalarg_count]
                  literalarg_count += 1
                elif util.is_str(conv):
                  if conv in extra_converters:
                    ev.value = extra_converters[conv](ev.value)
                  else:
                    raise ValueError("Could not perform conversion for filter subkey '{}/{}' with custom converter '{}'".format(k, ek, conv))
                else:
                  ev.value = conv(ev.value)
      else:
        # For each entry associated with this key...
        for ovl in output[k]:
          nonpos_subkeys = [posk for posk in ovl.keys() if posk is not PosArgs]
          if any(nonpos_subkeys):
            raise KeyError("Unexpected filter subkey(s) provided: {0}".format(nonpos_subkeys))
          # For each entry in the positional args list...
          for ov in ovl[PosArgs]:
            # Check the provided operator is valid in this scenario
            if ov.operator not in _get_valid_ops(_conversions[k]['fn']):
              raise KeyError("Invalid operator provided for filter key '{}'".format(k))
            # Do the conversions
            ov.value, continue_conv = _global_conv(ov.value, _conversions[k]['special'])
            if continue_conv:
              if ov.value == value_literalarg:
                if literalarg_count >= len(args):
                  raise ValueError("Query included more literal args ('{}') than argument objects provided to parse function".format(value_literalarg))
                ov.value = args[literalarg_count]
                literalarg_count += 1
              elif util.is_str(_conversions[k]['fn']):
                if _conversions[k]['fn'] in extra_converters:
                  ov.value = extra_converters[_conversions[k]['fn']](ov.value)
                else:
                  raise ValueError("Could not perform conversion for special converter '{}'".format(_conversions[k]['fn']))
              else:
                ov.value = _conversions[k]['fn'](ov.value)
    else:
      raise KeyError("Unexpected filter key provided: {0}".format(k))

  # We don't need to return OrderedDicts once processing is done, so use normal ones
  return {k: [dict(sv) for sv in v] for k, v in output.items()}


def normalise_filter_object(filters, strip_unexpected = False, anonymous_posargs = True, assume_ops = True):
  if not isinstance(filters, dict):
    raise ValueError("filter object must be a dict")
  output = filters
  for k in output:
    # Check we know about this key
    if k not in _conversions:
      if strip_unexpected:
        del output[k]
        continue
      else:
        raise ValueError("unexpected filter key '{}'".format(k))
    # Check the value is a list
    if not isinstance(output[k], list):
      output[k] = [output[k]]
    convdata = _conversions[k]
    # Check it hasn't been specified too many times
    if convdata['max'] is not None and len(output[k]) > convdata['max']:
      raise ValueError("filter key '{}' specified {} times, more than its maximum allowed {} times".format(k, len(output[k]), convdata['max']))
    # Start checking inner stuff
    for i in range(0, len(output[k])):
      if not isinstance(output[k][i], dict):
        if anonymous_posargs:
          output[k][i] = {PosArgs: output[k][i]}
        else:
          raise ValueError("filter key '{}' contains invalid value".format(k))
      for ek in output[k][i]:
        if not isinstance(output[k][i][ek], list):
          output[k][i][ek] = [output[k][i][ek]]
        # Ensure we have a relevant item in the convdata
        if ek is PosArgs:
          # If we're not simple data, we should either have a PosArgs entry or specific numeric entries
          if isinstance(convdata['fn'], dict):
            if ek not in convdata['fn'] and len(output[k][i][ek])-1 not in convdata['fn']:
              raise ValueError("filter key '{}' contains unexpected positional arguments".format(k))
            if ek in convdata['fn'] and convdata['fn'][ek]['max'] is not None and len(output[k][i][ek]) > convdata['fn'][ek]['max']:
              raise ValueError("filter key '{}' contains too many positional arguments".format(k))
        else:
          if not isinstance(convdata['fn'], dict):
            raise ValueError("filter key '{}' contains complex data with subkey '{}' when it should not".format(k, ek))
          if ek not in convdata['fn']:
            raise ValueError("filter key '{}' contains unexpected subkey '{}'".format(k, ek))
        for j in range(0, len(output[k][i][ek])):
          if not isinstance(output[k][i][ek][j], Operator):
            if assume_ops:
              conv_fn = convdata['fn']
              if isinstance(conv_fn, dict):
                conv_fn = conv_fn[ek]
              if isinstance(conv_fn, dict):
                conv_fn = conv_fn['fn']
              output[k][i][ek][j] = Operator(_assumed_operators.get(conv_fn, '='), output[k][i][ek][j])
            else:
              raise ValueError("filter key '{}/{}' was not an Operator object".format(k, ek))
  return output


def generate_sql(filters):
  select_str = []
  filter_str = []
  group_str = []
  order_str = []
  limit = None
  select_params = []
  filter_params = []
  group_params = []
  order_params = []
  req_tables = set()
  idx = 0

  if 'close_to' in filters:
    start_idx = idx
    req_tables.add('systems')
    for oentry in filters['close_to']:
      for entry in oentry[PosArgs]:
        pos = util.get_as_position(entry.value)
        select_str.append("(((? - systems.pos_x) * (? - systems.pos_x)) + ((? - systems.pos_y) * (? - systems.pos_y)) + ((? - systems.pos_z) * (? - systems.pos_z))) AS diff{0}".format(idx))
        select_params += [pos.x, pos.x, pos.y, pos.y, pos.z, pos.z]
        # For each operator and value...
        if 'distance' in oentry:
          for opval in oentry['distance']:
            filter_str.append("diff{} {} ? * ?".format(idx, opval.operator))
            filter_params += [opval.value, opval.value]
        idx += 1
        if 'direction' in oentry:
          for dentry in oentry['direction']:
            dpos = util.get_as_position(dentry.value)
            select_str.append("vec3_angle(systems.pos_x-?,systems.pos_y-?,systems.pos_z-?,?-?,?-?,?-?) AS diff{}".format(idx))
            select_params += [pos.x, pos.y, pos.z, dpos.x, pos.x, dpos.y, pos.y, dpos.z, pos.z]
            if 'angle' in oentry:
              for aentry in oentry['angle']:
                angle = aentry.value * math.pi / 180.0
                filter_str.append("diff{} {} ?".format(idx, aentry.operator))
                filter_params.append(angle)
            idx += 1
    order_str.append("+".join(["diff{}".format(i) for i in range(start_idx, idx)]))
  if 'allegiance' in filters:
    req_tables.add('systems')
    for oentry in filters['allegiance']:
      for entry in oentry[PosArgs]:
        if (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          filter_str.append("(systems.allegiance IS NOT NULL AND systems.allegiance != 'None')")
        elif (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          filter_str.append("(systems.allegiance IS NULL OR systems.allegiance == 'None')")
        else:
          extra_str = " OR systems.allegiance IS NULL OR systems.allegiance == 'None'"
          filter_str.append("(systems.allegiance {} ?{})".format(entry.operator, extra_str if entry.operator == '!=' else ''))
          filter_params.append(entry.value)
  if 'pad' in filters:
    req_tables.add('stations')
    for oentry in filters['pad']:
      for entry in oentry[PosArgs]:
        if (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          filter_str.append("stations.max_pad_size IS NULL")
        elif (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          filter_str.append("stations.max_pad_size IS NOT NULL")
        elif entry.operator in ['=','!=']:
          extra_str = " OR stations.max_pad_size IS NULL"
          filter_str.append("stations.max_pad_size {} ?{}".format(entry.operator, extra_str if entry.operator == '!=' else ''))
          filter_params.append(entry.value)
        else:
          valid_values = [p for p in PadSize.values if entry.matches(PadSize(p))]
          filter_str.append("stations.max_pad_size IN ({0})".format(",".join(["?"] * len(valid_values))))
          filter_params += valid_values
  if 'sc_distance' in filters:
    req_tables.add('stations')
    for oentry in filters['sc_distance']:
      for entry in oentry[PosArgs]:
        filter_str.append("stations.sc_distance {} ?".format(entry.operator))
        filter_params.append(entry.value)
    order_str.append("stations.sc_distance")
  if 'limit' in filters:
    limit = int(filters['limit'][0][PosArgs][0].value)

  return {
    'select': (select_str, select_params),
    'filter': (filter_str, filter_params),
    'order': (order_str, order_params),
    'group': (group_str, group_params),
    'limit': limit,
    'tables': list(req_tables)
  }


def filter(s_list, filters):
  limit = int(filters['limit'][0][PosArgs][0].value) if 'limit' in filters else None
  count = 0
  for s in s_list:
    if is_match(s, filters):
      if limit and count >= limit:
        return
      yield s
      count += 1


def is_match(s, filters):
  sy = s.system if isinstance(s, station.Station) else s
  st = s if isinstance(s, station.Station) else station.Station.none(s)
  if 'close_to' in filters:
    for oentry in filters['close_to']:
      for entry in oentry[PosArgs]:
        pos = util.get_as_position(entry.value)
        # For each operator and value...
        if 'distance' in oentry:
          for opval in oentry['distance']:
            if not opval.matches(sy.distance_to(pos)):
              return False
        if 'direction' in oentry:
          for dentry in oentry['direction']:
            dpos = util.get_as_position(dentry.value)
            cur_angle = (sy.position - pos).angle_to(dpos - pos)
            if 'angle' in oentry:
              for aentry in oentry['angle']:
                if not aentry.matches(cur_angle):
                  return False
  if 'allegiance' in filters:
    for oentry in filters['allegiance']:
      for entry in oentry[PosArgs]:
        # Handle Any/None carefully
        if (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          if sy.allegiance is None or sy.allegiance == 'None':
            return False
        elif (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          if sy.allegiance is not None and sy.allegiance != 'None':
            return False
        elif not entry.matches(sy.allegiance):
          return False
  if 'pad' in filters:
    for oentry in filters['pad']:
      for entry in oentry[PosArgs]:
        if (entry.operator == '=' and entry.value is None) or (entry.operator in ['!=','<>'] and entry.value is Any):
          if st.max_pad_size is not None:
            return False
        elif (entry.operator == '=' and entry.value is Any) or (entry.operator in ['!=','<>'] and entry.value is None):
          if st.max_pad_size is None:
            return False
        else:
          if not entry.matches(st.max_pad_size):
            return False
  if 'sc_distance' in filters:
    for oentry in filters['sc_distance']:
      for entry in oentry[PosArgs]:
        if not entry.matches(st.distance):
          return False
  return True
