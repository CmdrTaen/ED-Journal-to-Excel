import math
import sys
from . import ship
from .station import Station
from . import util

log = util.get_logger("calc")

default_slf = 0.9

default_ws_time = 15
jump_spool_time = 20  # 15s charge + 5s countdown
jump_cooldown_time = 10
default_jump_time = default_ws_time + jump_spool_time + jump_cooldown_time

sc_constant = 65
sc_multiplier = 1.8
sc_power = 0.5

stop_outpost_time = 75
stop_station_time = 90


def jump_count(a, b, jump_range, slf = default_slf):
  _, maxjumps = jump_count_range(a, b, jump_range, slf)
  return maxjumps

# Gets an estimated range of number of jumps required to jump from a to b
def jump_count_range(a, b, jump_range, slf = default_slf):
  legdist = a.distance_to(b)

  minjumps = int(math.ceil(legdist / jump_range))
  # If we're doing multiple jumps, apply the straight-line factor
  if legdist > jump_range:
    jump_range = jump_range * slf
  maxjumps = int(math.ceil(legdist / jump_range))
  return minjumps, maxjumps

# Calculate the fuel cost for a route, optionally taking lowered fuel usage into account
# Note that this method has no guards against routes beyond the tank size (i.e. negative fuel amounts)
def route_fuel_cost(route, ship, track_usage, starting_fuel = None):
  cost = 0.0
  cur_fuel = starting_fuel if starting_fuel is not None else ship.tank_size
  for i in range(1, len(route)):
    cost += ship.cost(route[i-1].distance_to(route[i]), cur_fuel)
    if track_usage:
      cur_fuel -= cost
  return cost

# The cost to go from a to b, as used in simple (non-routed) solving
def solve_cost(a, b, jump_range, witchspace_time = default_ws_time):
  hs_jumps = time_for_jumps(jump_count(a, b, jump_range), witchspace_time) * 2
  hs_jdist = a.distance_to(b)
  sc = sc_cost(b.distance if b.uses_sc else 0.0)
  return (hs_jumps + hs_jdist + sc)

# Gets the cumulative solve cost for a set of legs
def solve_route_cost(route, jump_range, witchspace_time = default_ws_time):
  cost = 0.0
  for i in range(0, len(route)-1):
    cost += solve_cost(route[i], route[i+1], jump_range, witchspace_time)
  return cost

# Gets the route cost for a trundle/trunkle route
def trundle_cost(route, ship):
  # Prioritise jump count: we should always be returning the shortest route
  jump_count = (len(route)-1) * 1000
  if ship is not None:
    # If we have ship info, use the real fuel calcs to generate the cost
    # Scale the result by the FSD's maxfuel to try and keep the magnitude consistent
    var = ship.range() * (route_fuel_cost(route, ship, False) / ship.fsd.maxfuel)
  else:
    # Without ship info, use a function of the square of the jump distances to try to create a balanced route
    var = math.sqrt(sum(l*l for l in [route[i+1].distance_to(route[i]) for i in range(len(route)-1)]))
  return (jump_count + var)

# Gets the route cost for an A* route
def astar_cost(a, b, route, jump_range, dist_threshold = None, witchspace_time = default_ws_time):
  jcount = jump_count(a, b, jump_range)
  hs_jumps = time_for_jumps(jcount, witchspace_time)
  hs_jdist = a.distance_to(b)
  var = route_variance(route, route[0].distance_to(route[-1]))

  penalty = 0.0
  # If we're allowing long jumps, we need to check whether to add an extra penalty
  # This is to disincentivise doing long jumps unless it's actually necessary
  if dist_threshold is not None:
    if jcount == 1 and a.distance_to(b) > dist_threshold:
      penalty += 20

    for i in range(0, len(route)-1):
      cdist = route[i+1].distance_to(route[i])
      if cdist > dist_threshold:
        penalty += 20

  return (hs_jumps + hs_jdist + var + penalty)

# Gets a very rough approximation of the time taken to stop at a starport/outpost
def station_time(stn):
  if isinstance(stn, Station) and stn.name is not None:
    if stn.max_pad_size == 'L':
      return stop_station_time
    else:
      return stop_outpost_time
  else:
    return 0.0

def time_for_jumps(jump_count, witchspace_time = default_ws_time):
  return max(0.0, ((jump_spool_time + witchspace_time) * jump_count) + (jump_cooldown_time * (jump_count - 1)))

# Gets the full time taken to traverse a route
def route_time(route, jump_count, witchspace_time = default_ws_time):
  hs_t = time_for_jumps(jump_count, witchspace_time)
  sc_t = sum(sc_time(stn) for stn in route[1:])
  stn_t = sum(station_time(stn) for stn in route)
  log.debug("hs_time = {0:.2f}, sc_time = {1:.2f}, stn_time = {2:.2f}", hs_t, sc_t, stn_t)
  return (hs_t + sc_t + stn_t)


# An approximation of the cost of doing an SC journey
# This is now flattened to avoid massive distances skewing things
def sc_cost(distance):
  return math.sqrt(sc_time(distance))

# An approximation of the amount of time taken to do an SC journey, in seconds
def sc_time(stn):
  if isinstance(stn, int) or isinstance(stn, float):
    return sc_constant + (math.pow(stn, sc_power) * sc_multiplier)
  elif isinstance(stn, Station) and stn.name is not None:
    return sc_time(stn.distance if stn.distance is not None else 0.0)
  else:
    return 0.0

# Get the cumulative actual distance of a set of jumps
def route_dist(route):
  dist = 0.0
  for i in range(0, len(route)-1):
    dist += route[i+1].distance_to(route[i])
  return dist

def route_variance(route, dist):
  return _route_sd_or_var(route, dist, 2)

def route_stdev(route, dist):
  return _route_sd_or_var(route, dist, 1)

def _route_sd_or_var(route, dist, power):
  if len(route) <= 1:
    return 0.0
  meanjump = dist / (len(route)-1)
  cvar = 0.0
  for i in range(0, len(route)-1):
    jdist = route[i+1].distance_to(route[i])
    cvar += math.pow((jdist - meanjump), power)
  return cvar


def astar(stars, sys_from, sys_to, valid_neighbour_fn, cost_fn):
  closedset = set()          # The set of nodes already evaluated.
  openset = set([sys_from])  # The set of tentative nodes to be evaluated, initially containing the start node
  came_from = dict()

  g_score = dict()
  g_score[sys_from] = 0      # Cost from sys_from along best known path.
  f_score = dict()
  f_score[sys_from] = cost_fn(sys_from, sys_to, [sys_from])

  while len(openset) > 0:
    current = min(openset, key=f_score.get)  # the node in openset having the lowest f_score[] value
    if current == sys_to:
      return _astar_reconstruct_path(came_from, sys_to)

    openset.remove(current)
    closedset.add(current)

    neighbor_nodes = [n for n in stars if valid_neighbour_fn(n, current)]

    path = _astar_reconstruct_path(came_from, current)

    for neighbor in neighbor_nodes:
      if neighbor in closedset:
        continue

      # tentative_g_score = g_score[current] + (current.position - neighbor.position).length
      tentative_g_score = g_score[current] + cost_fn(current, neighbor, path)

      if neighbor not in g_score:
        g_score[neighbor] = sys.float_info.max

      if neighbor not in openset or tentative_g_score < g_score[neighbor]:
        came_from[neighbor] = current
        g_score[neighbor] = tentative_g_score
        f_score[neighbor] = cost_fn(neighbor, sys_to, _astar_reconstruct_path(came_from, neighbor))
        openset.add(neighbor)

  return None

def _astar_reconstruct_path(came_from, current):
  total_path = [current]
  while current in came_from:
      current = came_from[current]
      total_path.append(current)
  return list(reversed(total_path))

