/* OpenTTD Phase 8.6 fixture, GPL-2.0-only: stations, stops, depots, a dock, a buoy, a ship depot and a lock near the largest town. */
class Stations3DFixture extends AIController {
 function Abs(v) { return v < 0 ? -v : v; }

 /* The first tile on rings r0..r1 round (cx, cy) for which fn returns true. */
 function Spiral(cx, cy, r0, r1, fn) {
  for (local r = r0; r <= r1; r++) {
   for (local dx = -r; dx <= r; dx++) for (local dy = -r; dy <= r; dy++) {
    if (Abs(dx) != r && Abs(dy) != r) continue;
    local tile = AIMap.GetTileIndex(cx + dx, cy + dy);
    if (AIMap.IsValidTile(tile) && fn(tile)) return tile;
   }
  }
  return null;
 }

 function Report(what, tile) {
  if (tile == null) print("PHASE8 FIXTURE " + what + " failed");
  else print("PHASE8 FIXTURE " + what + " x=" + AIMap.GetTileX(tile) + " y=" + AIMap.GetTileY(tile));
 }

 function Start() {
  AICompany.SetName("3D Stations");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local town = towns.Begin();
  local centre = AITown.GetLocation(town);
  local cx = AIMap.GetTileX(centre), cy = AIMap.GetTileY(centre);
  print("PHASE8 FIXTURE town=" + AITown.GetName(town) + " x=" + cx + " y=" + cy);
  local X = AIMap.GetTileIndex(1, 0), Y = AIMap.GetTileIndex(0, 1);

  /* Rail: a 3x5 station (the default layout gives the odd first platform a small building, bare platform ends and both
   * large-building roofs elsewhere), a 1x3 one on the other axis,
   * depots facing SE and NE, and a waypoint on a short line. */
  AIRail.SetCurrentRailType(AIRailTypeList().Begin());
  Report("rail_station_x", Spiral(cx, cy, 6, 30, function(t) { return AIRail.BuildRailStation(t, AIRail.RAILTRACK_NE_SW, 3, 5, AIStation.STATION_NEW); }));
  Report("rail_station_y", Spiral(cx, cy, 6, 30, function(t) { return AIRail.BuildRailStation(t, AIRail.RAILTRACK_NW_SE, 1, 3, AIStation.STATION_NEW); }));
  Report("rail_depot_se", Spiral(cx, cy, 5, 30, function(t) : (Y) { return AITile.IsBuildable(t) && AIRail.BuildRailDepot(t, t + Y); }));
  Report("rail_depot_ne", Spiral(cx, cy, 5, 30, function(t) : (X) { return AITile.IsBuildable(t) && AIRail.BuildRailDepot(t, t - X); }));
  Report("rail_waypoint", Spiral(cx, cy, 5, 30, function(t) : (X) {
   if (!AITile.IsBuildable(t - X) || !AITile.IsBuildable(t) || !AITile.IsBuildable(t + X)) return false;
   if (!AIRail.BuildRail(t - X, t, t + X)) return false;
   return AIRail.BuildRailWaypoint(t);
  }));

  /* Road: bus and lorry bays (entrances SE and NE), drive-through stops on short new roads, a depot. */
  AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
  Report("bus_bay", Spiral(cx, cy, 4, 30, function(t) : (Y) { return AITile.IsBuildable(t) && AIRoad.BuildRoadStation(t, t + Y, AIRoad.ROADVEHTYPE_BUS, AIStation.STATION_NEW); }));
  Report("truck_bay", Spiral(cx, cy, 4, 30, function(t) : (X) { return AITile.IsBuildable(t) && AIRoad.BuildRoadStation(t, t - X, AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW); }));
  foreach (kind in [["bus_drive", AIRoad.ROADVEHTYPE_BUS], ["truck_drive", AIRoad.ROADVEHTYPE_TRUCK]]) {
   Report(kind[0], Spiral(cx, cy, 4, 30, function(t) : (X, kind) {
    if (!AITile.IsBuildable(t - X) || !AITile.IsBuildable(t) || !AITile.IsBuildable(t + X)) return false;
    if (!AIRoad.BuildRoad(t - X, t + X)) return false;
    return AIRoad.BuildDriveThroughRoadStation(t, t + X, kind[1], AIStation.STATION_NEW);
   }));
  }
  Report("road_depot", Spiral(cx, cy, 4, 30, function(t) : (Y) { return AITile.IsBuildable(t) && AIRoad.BuildRoadDepot(t, t + Y); }));

  /* Water: the coast nearest the town gets a dock; a buoy and a ship depot on the sea beside it; a lock on a slope. */
  local dock = Spiral(cx, cy, 1, 120, function(t) { return AITile.IsCoastTile(t) && AIMarine.BuildDock(t, AIStation.STATION_NEW); });
  Report("dock", dock);
  if (dock != null) {
   local dx = AIMap.GetTileX(dock), dy = AIMap.GetTileY(dock);
   Report("buoy", Spiral(dx, dy, 3, 20, function(t) { return AITile.IsWaterTile(t) && AIMarine.BuildBuoy(t); }));
   Report("ship_depot", Spiral(dx, dy, 3, 20, function(t) : (X) { return AITile.IsWaterTile(t) && AIMarine.BuildWaterDepot(t, t + X); }));
   Report("ship_depot_y", Spiral(dx, dy, 3, 20, function(t) : (Y) { return AITile.IsWaterTile(t) && AIMarine.BuildWaterDepot(t, t + Y); }));
  }
  Report("lock", Spiral(cx, cy, 2, 60, function(t) {
   local s = AITile.GetSlope(t);
   if (s != AITile.SLOPE_NE && s != AITile.SLOPE_SE && s != AITile.SLOPE_SW && s != AITile.SLOPE_NW) return false;
   return AIMarine.BuildLock(t);
  }));
  print("PHASE8 FIXTURE done");
  while (true) this.Sleep(1000);
 }
}
