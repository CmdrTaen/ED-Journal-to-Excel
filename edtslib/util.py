import collections
import logging
import math
import numbers
import os
import platform
import re
import socket
import ssl
import sys
import timeit

from . import defs
from . import vector3
from .thirdparty import gzipinputstream as gzis

if sys.version_info >= (3, 0):
  import urllib.parse
  import urllib.request
  import urllib.error
else:
  import urllib2
  import urllib
  import urlparse

# Slightly ugly classes to allow new-style {} formatting in log messages without always executing them
class _BraceString(str):
  def __mod__(self, other): return self.format(*other)
  def __str__(self): return self
class _StyleAdapter(logging.LoggerAdapter):
  def process(self, msg, kwargs): return _BraceString(msg), kwargs

def get_logger(name):
  return _StyleAdapter(logging.getLogger(name), None)


def configure_logging(log_level):
  logging.basicConfig(level=convert_log_level(log_level), format="[%(asctime)-8s.%(msecs)03d] [%(name)-10s] [%(levelname)7s] %(message)s", datefmt=defs.log_dateformat)

def set_verbosity(level):
  logging.getLogger().setLevel(convert_log_level(level))

def convert_log_level(level):
  if level >= 3:
    return logging.DEBUG
  elif level >= 2:
    return logging.INFO
  elif level >= 1:
    return logging.WARN
  elif level >= 0:
    return logging.ERROR
  else:
    return logging.CRITICAL

log = get_logger("util")

USER_AGENT = '{}/{}'.format(defs.name, defs.version)

# Match a float such as "33", "-33", "-33.1"
_rgxstr_float = r'[-+]?\d+(?:\.\d+)?'
# Match a set of coords such as "[33, -45.6, 78.910]"
_rgxstr_coords = r'^\[\s*(?P<x>{0})\s*[,/]\s*(?P<y>{0})\s*[,/]\s*(?P<z>{0})\s*\](?:=(?P<name>.+))?$'.format(_rgxstr_float)
# Compile the regex for faster execution later
_regex_float = re.compile('^' + _rgxstr_float + '$')
_regex_coords = re.compile(_rgxstr_coords)

def parse_coords(sysname):
  rx_match = _regex_coords.match(sysname)
  if rx_match is not None:
    # If it matches, make a fake system and station at those coordinates
    try:
      cx = float(rx_match.group('x'))
      cy = float(rx_match.group('y'))
      cz = float(rx_match.group('z'))
      name = rx_match.group('name') if rx_match.group('name') is not None else sysname
      return (cx, cy, cz, name)
    except Exception as ex:
      log.debug("Failed to parse manual system: {}", ex)
  return None


def _open_url_inner_py3(url, headers, allow_no_ssl):
  # Specify our own user agent as Cloudflare doesn't seem to like the urllib one
  request = urllib.request.Request(url, headers=headers)
  try:
    return urllib.request.urlopen(request)
  except urllib.error.HTTPError as err:
    log.error("Error {0} opening {1}: {2}", err.code, url, err.reason)
    return None

def _open_url_inner_py2(url, headers, allow_no_ssl):
  sslctx = None
  try:
    sslctx = ssl.SSLContext(ssl.PROTOCOL_TLSv1)
    # If we're on OSX with OpenSSL 0.9.x, manually specify preferred ciphers so CloudFlare can negotiate successfully
    if platform.system() == 'Darwin' and ssl.OPENSSL_VERSION_INFO[0] < 1:
      sslctx.set_ciphers("ECCdraft:HIGH:!aNULL")
  except Exception as ex:
    if allow_no_ssl:
      log.warning("Failed to create SSL context ({0}), attempting to continue", str(ex))
    else:
      log.error("Failed to create SSL context: {0}", str(ex))
      return None
  # Specify our own user agent as Cloudflare doesn't seem to like the urllib one
  request = urllib2.Request(url, headers=headers)
  try:
    return urllib2.urlopen(request, context=sslctx)
  except urllib2.HTTPError as err:
    log.error("Error {0} opening {1}: {2}", err.code, url, err.reason)
    return None

_open_url_inner = _open_url_inner_py3 if sys.version_info >= (3, 0) else _open_url_inner_py2

def open_url(url, allow_gzip = True, allow_no_ssl = False):
  headers = {'User-Agent': USER_AGENT}
  if allow_gzip:
    headers['Accept-Encoding'] = 'gzip'
  response = _open_url_inner(url, headers, allow_no_ssl)
  if response and response.info().get('Content-Encoding') == 'gzip':
    try:
      return gzis.GzipInputStream(response)
    except:
      log.error("Error decompressing {0}", url)
      return None
  else:
    return response


def _read_stream_line_inner_py3(stream): return stream.readline().decode("utf-8")
def _read_stream_line_inner_py2(stream): return stream.readline()
_read_stream_line_inner = _read_stream_line_inner_py3 if sys.version_info >= (3, 0) else _read_stream_line_inner_py2

def read_stream_line(stream):
  try:
    return _read_stream_line_inner(stream)
  except socket.error as e:
    if e.errno == socket.errno.ECONNRESET:
      log.warning("Received ECONNRESET while reading line from socket-based stream")
      return None
    else:
      raise

def _read_stream_inner_py3(stream, limit):
  return stream.read(limit).decode("utf-8")
def _read_stream_inner_py2(stream, limit):
  if limit is None and not isinstance(stream, gzis.GzipInputStream):
    limit = -1
  return stream.read(limit)
_read_stream_inner = _read_stream_inner_py3 if sys.version_info >= (3, 0) else _read_stream_inner_py2

def read_stream(stream, limit = None):
  try:
    return _read_stream_inner(stream, limit)
  except socket.error as e:
    if e.errno == socket.errno.ECONNRESET:
      log.warning("Received ECONNRESET while reading from socket-based stream")
      return None
    else:
      raise

def read_from_url(url, allow_gzip = True, allow_no_ssl = False):
  return read_stream(open_url(url, allow_gzip=allow_gzip, allow_no_ssl=allow_no_ssl))

def _write_stream_py3(stream, data): return stream.write(data.encode("utf-8"))
def _write_stream_py2(stream, data): return stream.write(data)
write_stream = _write_stream_py3 if sys.version_info >= (3, 0) else _write_stream_py2

def _path_to_url_py3(path): return urllib.parse.urljoin('file:', urllib.request.pathname2url(os.path.abspath(path)))
def _path_to_url_py2(path): return urlparse.urljoin('file:', urllib.pathname2url(os.path.abspath(path)))
path_to_url = _path_to_url_py3 if sys.version_info >= (3, 0) else _path_to_url_py2

def get_relative_path(p1, p2):
  common_prefix = os.path.commonprefix([os.path.abspath(p1), os.path.abspath(p2)])
  p1r = os.path.relpath(p1, common_prefix)
  p2r = os.path.relpath(p2, common_prefix)
  return p1r if len(p1r) >= len(p2r) else p2r

def is_interactive():
  return hasattr(sys, 'ps1')

def _is_str_py3(s): return isinstance(s, str)
def _is_str_py2(s): return isinstance(s, basestring)
is_str = _is_str_py3 if sys.version_info >= (3, 0) else _is_str_py2

def _download_file_py3(url, file): return urllib.request.urlretrieve(url, file)
def _download_file_py2(url, file): return urllib2.urlretrieve(url, file)
download_file = _download_file_py3 if sys.version_info >= (3, 0) else _download_file_py2


def string_bool(s):
  return s.lower() in ("yes", "true", "1")


def hex2str(s):
  return ''.join(chr(int(s[i:i+2], 16)) for i in range(0, len(s), 2))


def parse_number_or_add_percentage(value, basevalue):
  if value is None or not _regex_float.match(value.strip('%')):
    return None
  if value.endswith('%'):
    return float(basevalue) * (1.0 + (float(value.strip('%')) / 100.0))
  else:
    return float(value)


def int2hex(i, l=64):
  fmtlen = str(int(int(l)/4))
  return ('{0:0'+fmtlen+'X}').format(i)

def _get_bytes_py3(s, enc = 'utf-8'): return bytes(s, enc)
def _get_bytes_py2(s, enc = 'utf-8'): return bytes(s)
get_bytes = _get_bytes_py3 if sys.version_info >= (3, 0) else _get_bytes_py2


# 32-bit hashing algorithm found at http://papa.bretmulvey.com/post/124027987928/hash-functions
# Seemingly originally by Bob Jenkins <bob_jenkins-at-burtleburtle.net> in the 1990s
def jenkins32(key):
  key += (key << 12)
  key &= 0xFFFFFFFF
  key ^= (key >> 22)
  key += (key << 4)
  key &= 0xFFFFFFFF
  key ^= (key >> 9)
  key += (key << 10)
  key &= 0xFFFFFFFF
  key ^= (key >> 2)
  key += (key << 7)
  key &= 0xFFFFFFFF
  key ^= (key >> 12)
  return key


# Grabs the value from the first N bits, then return a right-shifted remainder
def unpack_and_shift(value, bits):
  return (value >> bits, value & (2**bits-1))

# Shifts existing data left by N bits and adds a new value into the "empty" space
def pack_and_shift(value, new_data, bits):
  return (value << bits) + (new_data & (2**bits-1))

# Interleaves two values, starting at least significant bit
# e.g. (0b1111, 0b0000) --> (0b01010101)
def interleave(val1, val2, maxbits):
  output = 0
  for i in range(0, maxbits//2 + 1):
    output |= ((val1 >> i) & 1) << (i*2)
  for i in range(0, maxbits//2 + 1):
    output |= ((val2 >> i) & 1) << (i*2 + 1)
  return output & (2**maxbits - 1)

# Deinterleaves two values, starting at least significant bit
# e.g. (0b00110010) --> (0b0100, 0b0101)
def deinterleave(val, maxbits):
  out1 = 0
  out2 = 0
  for i in range(0, maxbits, 2):
    out1 |= ((val >> i) & 1) << (i//2)
  for i in range(1, maxbits, 2):
    out2 |= ((val >> i) & 1) << (i//2)
  return (out1, out2)


def get_as_position(v):
  if v is None:
    return None
  # If it's already a vector, all is OK
  if isinstance(v, vector3.Vector3):
    return v
  if hasattr(v, "position"):
    return v.position
  if hasattr(v, "centre"):
    return v.centre
  if hasattr(v, "system"):
    return get_as_position(v.system)
  try:
    if len(v) == 3 and all([isinstance(i, numbers.Number) for i in v]):
      return vector3.Vector3(v[0], v[1], v[2])
  except:
    pass
  return None

def flatten(listish):
  return [i for sublist in [listish] for i in sublist] if (isinstance(listish, collections.Iterable) and not is_str(listish)) else [listish]

def format_seconds(seconds, milliseconds = False):
  interval = ''
  if seconds > 86400:
    d = int(math.floor(seconds / 86400))
    interval += '{}d'.format(d)
    seconds -= d * 86400
  if seconds > 3600:
    h = int(math.floor(seconds / 3600))
    interval += '{}h'.format(h)
    seconds -= h * 3600
  if seconds > 60:
    m = int(math.floor(seconds / 60))
    interval += '{}m'.format(m)
    seconds -= m * 60
  if seconds:
    interval += '{}s'.format('{:.4f}' if milliseconds else '{:.0f}').format(seconds)
  return interval

def start_timer():
  return timeit.default_timer()

def get_timer(start):
  return start_timer() - start

def format_timer(start):
  return format_seconds(get_timer(start), True)
