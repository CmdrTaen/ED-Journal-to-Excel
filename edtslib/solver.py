import math
import random
import sys
import time

from . import calc
from . import util
from . import vector3

log = util.get_logger("solver")

max_single_solve_size = 8
cluster_size_max = 8
cluster_size_min = 1
cluster_divisor = 10
cluster_iteration_limit = 50
cluster_repeat_limit = 100
cluster_route_search_limit = 4
supercluster_size_max = 8


CLUSTERED         = "clustered"
CLUSTERED_REPEAT  = "clustered-repeat"
BASIC             = "basic"
NEAREST_NEIGHBOUR = "nearest-neighbour"
modes = [CLUSTERED, CLUSTERED_REPEAT, BASIC, NEAREST_NEIGHBOUR]


class _Cluster(object):
  def __init__(self, objs, mean):
    self.position = mean
    self.systems = objs

  @property
  def is_supercluster(self):
    return any(isinstance(s, _Cluster) for s in self.systems)

  def get_closest(self, target):
    best = None
    bestdist = sys.float_info.max
    for s in self.systems:
      if isinstance(s, _Cluster) and s.is_supercluster:
        newsys, newdist = s.get_closest(target)
        if newdist < bestdist:
          best = newsys
          bestdist = newdist
      else:
        newdist = (s.position - target.position).length
        if newdist < bestdist:
          best = s
          bestdist = newdist
    return best, bestdist

  def __repr__(self):
    return "Cluster(size={}, pos={})".format(len(self.systems), self.position)


class Solver(object):
  def __init__(self, jump_range, diff_limit, witchspace_time = calc.default_ws_time):
    self._diff_limit = diff_limit
    self._jump_range = jump_range
    self._ws_time = witchspace_time


  def solve(self, tours, stations, start, end, maxstops, preferred_mode = CLUSTERED):
    if all(len(t) < 2 for t in tours):
      log.debug("No tours forming valid constraints detected, ignoring them all")
      tours = None

    timer = util.start_timer()

    # If the user asked for clustered but the number of destinations is small enough, just use basic
    if preferred_mode in (CLUSTERED_REPEAT, CLUSTERED) and len(stations) <= max_single_solve_size:
      preferred_mode = BASIC

    log.debug("Solving set using preferred mode '{}'", preferred_mode)
    if preferred_mode == CLUSTERED_REPEAT:
      result = self.solve_clustered_repeat(tours, stations, start, end, maxstops), False
    elif preferred_mode == CLUSTERED:
      result = self.solve_clustered(tours, stations, start, end, maxstops), False
    elif preferred_mode == BASIC:
      result = self.solve_basic(tours, stations, start, end, maxstops), True
    elif preferred_mode == NEAREST_NEIGHBOUR:
      result = self.solve_nearest_neighbour(tours, stations, start, end, maxstops), True
    else:
      log.error("Tried to use invalid preferred mode {}", preferred_mode)
      result = None

    log.debug("Solve from {} to {} using mode {} finished after {}", start, end, preferred_mode, util.format_timer(timer))
    return result

  def solve_basic(self, tours, stations, start, end, maxstops):
    result, _ = self.solve_basic_with_cost(tours, stations, start, end, maxstops)
    return result


  def solve_basic_with_cost(self, tours, stations, start, end, maxstops):
    if not any(stations):
      if start == end:
        return [start], 0.0
      else:
        return [start, end], calc.solve_cost(start, end, self._jump_range, witchspace_time=self._ws_time)

    count = 0
    mincost = None
    minroute = None

    reversible = tours is None or all(len(t) < 2 for t in tours)

    log.debug("Calculating and checking viable routes...")
    vr = self._get_viable_routes([start], tours, stations, end, maxstops)

    for route in vr:
      count += 1
      cost_normal = calc.solve_route_cost(route, self._jump_range, witchspace_time=self._ws_time)
      if reversible:
        route_reversed = [route[0]] + list(reversed(route[1:-1])) + [route[-1]]
        cost_reversed = calc.solve_route_cost(route_reversed, self._jump_range, witchspace_time=self._ws_time)

        cost = cost_normal if (cost_normal <= cost_reversed) else cost_reversed
        route = route if (cost_normal <= cost_reversed) else route_reversed
      else:
        cost = cost_normal

      if mincost is None or cost < mincost:
        log.debug("New minimum cost: {0} on viable route #{1}", cost, count)
        mincost = cost
        minroute = route
    log.debug("Checked {0} viable routes", count)

    return minroute, mincost


  def solve_nearest_neighbour(self, tours, stations, start, end, maxstops):
    result, _ = self.solve_nearest_neighbour_with_cost(tours, stations, start, end, maxstops)
    return result

  def solve_nearest_neighbour_with_cost(self, tours, stations, start, end, maxstops):
    route = [start]
    full_cost = 0
    remaining = stations
    while any(remaining) and len(route)+1 < maxstops:
      cur_cost = sys.maxsize
      cur_stop = None
      for s in remaining:
        if tours and not self._check_tour_route(route[1:], tours, s):
          continue
        cost = calc.solve_cost(route[-1], s, self._jump_range, witchspace_time=self._ws_time)
        if cost < cur_cost:
          cur_stop = s
          cur_cost = cost
      if cur_stop is not None:
        route.append(cur_stop)
        remaining.remove(cur_stop)
        full_cost += cur_cost
        log.debug("Added system to current NN route: {}, new len {}, new cost {}", cur_stop, len(route), full_cost)
    route.append(end)
    return route, cur_cost


  def solve_clustered(self, tours, stations, start, end, maxstops):
    result, _ = self.solve_clustered_with_cost(tours, stations, start, end, maxstops)
    return result

  def solve_clustered_with_cost(self, tours, stations, start, end, maxstops):
    cluster_count = int(math.ceil(float(len(stations) + 2) / cluster_divisor))
    log.debug("Splitting problem into {0} clusters...", cluster_count)
    clusters = find_centers(stations, cluster_count)
    clusters = self._resolve_cluster_sizes(clusters)

    sclusters = self._get_best_supercluster_route(clusters, start, end)

    route = [start]
    cost = 0
    r_maxstops = maxstops - 2

    # Get the closest points in the first/last clusters to the start/end
    _, from_start = self._get_closest_points([start], sclusters[0].systems)
    to_end, _ = self._get_closest_points(sclusters[-1].systems, [end])
    # For each cluster...
    for i in range(0, len(sclusters)-1):
      log.debug("Solving for cluster at index {}...", i)
      from_cluster = sclusters[i]
      to_cluster = sclusters[i+1]
      # Get the closest points, disallowing using from_start or to_end
      from_end, to_start = self._get_closest_points(from_cluster.systems, to_cluster.systems, [from_start, to_end])
      # Work out how many of the stops we should be doing in this cluster
      cur_maxstops = min(len(from_cluster.systems), int(round(float(maxstops) * len(from_cluster.systems) / len(stations))))
      r_maxstops -= cur_maxstops
      # Solve and add to the route. DO NOT allow nested clustering, that makes it all go wrong :)
      newroute, newcost = self.solve_basic_with_cost(tours, [c for c in from_cluster.systems if c not in [from_start, from_end]], from_start, from_end, cur_maxstops)
      route += newroute
      cost += newcost
      from_start = to_start
    newroute, newcost = self.solve_basic_with_cost(tours, [c for c in sclusters[-1].systems if c not in [from_start, to_end]], from_start, to_end, r_maxstops)
    route += newroute
    cost += newcost
    route += [end]
    return route, cost


  def solve_clustered_repeat(self, tours, stations, start, end, maxstops, iterations = cluster_repeat_limit):
    result, _ = self.solve_clustered_repeat_with_cost(tours, stations, start, end, maxstops, iterations)
    return result

  def solve_clustered_repeat_with_cost(self, tours, stations, start, end, maxstops, iterations = cluster_repeat_limit):
    minroute = None
    mincost = sys.float_info.max
    for _ in range(0, iterations):
      route, cost = self.solve_clustered_with_cost(tours, stations, start, end, maxstops)
      if cost < mincost:
        mincost = cost
        minroute = route
    return minroute, mincost


  def _resolve_cluster_sizes(self, pclusters):
    clusters = list(pclusters)
    iterations = 0
    while iterations < cluster_iteration_limit:
      iterations += 1
      for i,c in enumerate(clusters):
        if c.is_supercluster:
          c.systems = self._resolve_cluster_sizes(c.systems)
        if len(c.systems) > cluster_size_max:
          log.debug("Splitting oversized cluster {} into two", c)
          del clusters[i]
          newclusters = find_centers(c.systems, 2)
          clusters += newclusters
          break
      lengths = [len(c.systems) for c in clusters]
      # If the current state is good, check supercluster size
      if min(lengths) >= cluster_size_min and max(lengths) <= cluster_size_max:
        if len(clusters) <= supercluster_size_max:
          break
        else:
          # Too many clusters, consolidate
          subdiv = int(math.ceil(float(len(clusters)) / supercluster_size_max))
          log.debug("Consolidating from {} to {} superclusters", len(clusters), subdiv)
          clusters = find_centers(clusters, subdiv)
          lengths = [len(c.systems) for c in clusters]
          # If everything is now valid...
          if min(lengths) >= cluster_size_min and max(lengths) <= cluster_size_max and len(clusters) <= supercluster_size_max:
              break
    clusters = [c for c in clusters if any(c.systems)]
    log.debug("Using clusters of sizes {} after {} iterations", ", ".join([str(len(c.systems)) for c in clusters]), iterations)
    return clusters


  def _check_tour_route(self, route, tours, station):
    if not tours:
      return True
    for tour in tours:
      # Tour must have at least two elements to form a valid constraint.
      if len(tour) < 2:
        continue
      try:
        index = tour.index(station)
      except ValueError:
        # This station is not part of the tour.
        continue
      if len(route) <= index:
        # The station is the nth in the tour but there are at most n
        # elements in the route already, so the station can only be
        # valid if it's the first in the route.
        if len(route) or index:
          # Optimisation: The station would be rejected anyway after
          # building the list of tour elements already in the route,
          # but rejecting it here saves building that list, which is
          # done more often and takes longer as the number of total
          # stations grows.
          return False
      indices = []
      for t in tour:
        try:
          indices.append(route.index(t))
        except ValueError:
          pass
      if index > len(indices):
        # The station would be inserted out of sequence.
        return False
    return True

  def _get_viable_routes(self, route, tours, stations, end, maxstops):
    # If we have more non-end stops to go...
    if len(route) + 1 < maxstops:
      nexts = {}

      for stn in stations:
        # If this station already appears in the route, do more checks
        if stn in route or stn == end:
          # If stn is in the route at least the number of times it's in the original list, ignore it
          # Add 1 to the count if the start station is *also* the same, since this appears in route but not in stations
          route_matches = len([rs for rs in route if rs == stn])
          stn_matches = len([rs for rs in stations if rs == stn]) + (1 if stn == route[0] else 0)
          if route_matches >= stn_matches:
            continue
        # Check that adding this station would not break any tour constraints.
        if tours and not self._check_tour_route(route[1:], tours, stn):
          continue

        dist = calc.solve_cost(route[-1], stn, self._jump_range, witchspace_time=self._ws_time)
        nexts[stn] = dist

      if len(nexts):
        mindist = min(nexts.values())

        for stn, dist in nexts.items():
          if dist <= (mindist * self._diff_limit):
            # For each valid next stop, run
            for r in self._get_viable_routes(route + [stn], tours, stations, end, maxstops):
              yield r

    # We're at the end
    else:
      route.append(end)
      yield route


  def _get_best_supercluster_route(self, clusters, start, end):
    if len(clusters) == 1:
      return list(clusters)
    first = min(clusters, key=lambda t: t.get_closest(start)[1])
    last = min([c for c in clusters if c != first], key=lambda t: t.get_closest(end)[1])
    log.debug("Calculating supercluster route from {} --> {}", first, last)
    log.debug("Clusters: {}", clusters)
    if len(clusters) > 3:
      log.debug("Calculating cluster route for {}", clusters)
      inter, _ = self._get_best_cluster_route([c for c in clusters if c not in [first, last]], first, last)
    else:
      inter = [c for c in clusters if c not in [first, last]]
    proute = [first] + inter + [last]
    route = []
    for i,c in enumerate(proute):
      if isinstance(c, _Cluster) and c.is_supercluster:
        log.debug("Going deeper... i={}, c={}", i, c)
        route += self._get_best_supercluster_route(c.systems, start if i == 0 else route[i-1], end if i >= len(route)-1 else route[i+1])
      else:
        route.append(c)
    return route


  def _get_best_cluster_route(self, clusters, start, end, route = []):
    best = None
    bestcost = sys.float_info.max
    if not route:
      log.debug("In get_best_cluster_route, input = {}, start = {}, end = {}", clusters, start, end)
    if len(route) < len(clusters):
      startpt = route[-1].position if any(route) else start.position
      sclusters = sorted([c for c in clusters if c not in route], key=lambda t: (startpt - t.position).length)
      # print("route:", route, "smeans:", smeans)
      for i in range(0, min(len(sclusters), cluster_route_search_limit)):
        c_route, c_cost = self._get_best_cluster_route(clusters, start, end, route + [sclusters[i]])
        if c_cost < bestcost:
          best = c_route
          bestcost = c_cost
    else:
      cur_cost = (start.position - route[0].position).length
      for i in range(1, len(route)):
        cur_cost += (route[i-1].position - route[i].position).length
      cur_cost += (route[-1].position - end.position).length
      best = route
      bestcost = cur_cost
    return (best, bestcost)


  def _get_closest_points(self, cluster1, cluster2, disallowed = []):
    best = None
    bestcost = None
    for n1 in cluster1:
      if n1 in disallowed and len(cluster1) > 1: # If len(cluster) is 1, start == end so allow it
        continue
      for n2 in cluster2:
        if n2 in disallowed and len(cluster2) > 1: # If len(cluster) is 1, start == end so allow it
          continue
        cost = calc.solve_cost(n1, n2, self._jump_range, witchspace_time=self._ws_time)
        if best is None or cost < bestcost:
          best = (n1, n2)
          bestcost = cost
    return best


#
# K-means clustering
#
def _cluster_points(X, mu):
  clusters = [[] for i in range(len(mu))]
  for x in X:
    bestmukey = min([(i[0], (x.position - mu[i[0]]).length) for i in enumerate(mu)], key=lambda t: t[1])[0]
    clusters[bestmukey].append(x)
  return clusters


def _reevaluate_centers(mu, clusters):
  return [vector3.mean([x.position for x in c]) for c in clusters]


def _has_converged(mu, oldmu):
  return (set(mu) == set(oldmu))


def find_centers(X, K):
  # Initialize to K random centers
  oldmu = random.sample([x.position for x in X], K)
  mu = random.sample([x.position for x in X], K)
  clusters = _cluster_points(X, mu)
  while not _has_converged(mu, oldmu):
    oldmu = mu
    # Assign all points in X to clusters
    clusters = _cluster_points(X, mu)
    # Reevaluate centers
    mu = _reevaluate_centers(oldmu, clusters)
  return [_Cluster(clusters[i], mu[i]) for i in range(len(mu))]
