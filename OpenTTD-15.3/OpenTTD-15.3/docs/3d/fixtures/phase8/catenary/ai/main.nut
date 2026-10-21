/* OpenTTD Phase 8.6 fixture, GPL-2.0-only: electrified track in every catenary situation through ordinary commands,
 * near the largest town. On one 26 x 16 levelled site at (sx, sy): a long X line that climbs over a raised block, a Y line
 * crossing it (junction) and a road (level crossing), a diagonal line, a two-platform station with a depot and an
 * electric train, a rail tunnel through the raised block and a rail bridge along Y. */
class Catenary3DFixture extends AIController {
 function Abs(v) { return v < 0 ? -v : v; }
 function Tile(x, y) { return AIMap.GetTileIndex(x, y); }

 /* The first tile on rings r0..r1 round (cx, cy) for which fn returns true. */
 function Spiral(cx, cy, r0, r1, fn) {
  for (local r = r0; r <= r1; r++) {
   for (local dx = -r; dx <= r; dx++) for (local dy = -r; dy <= r; dy++) {
    if (Abs(dx) != r && Abs(dy) != r) continue;
    local tile = Tile(cx + dx, cy + dy);
    if (AIMap.IsValidTile(tile) && fn(tile)) return tile;
   }
  }
  return null;
 }

 /* w x h tiles from t, all buildable, flat and at one height. */
 function FlatArea(t, w, h) {
  local x0 = AIMap.GetTileX(t), y0 = AIMap.GetTileY(t), z = AITile.GetMinHeight(t);
  for (local x = x0; x < x0 + w; x++) for (local y = y0; y < y0 + h; y++) {
   local u = Tile(x, y);
   if (!AIMap.IsValidTile(u) || !AITile.IsBuildable(u) || AITile.GetSlope(u) != AITile.SLOPE_FLAT || AITile.GetMinHeight(u) != z) return false;
  }
  return true;
 }

 /* w x h tiles from t, all buildable. */
 function Buildable(t, w, h) {
  local x0 = AIMap.GetTileX(t), y0 = AIMap.GetTileY(t);
  for (local x = x0; x < x0 + w; x++) for (local y = y0; y < y0 + h; y++) {
   local u = Tile(x, y);
   if (!AIMap.IsValidTile(u) || !AITile.IsBuildable(u)) return false;
  }
  return true;
 }

 function Report(what, ok, x, y) {
  if (!ok) print("PHASE8 FIXTURE " + what + " failed: " + AIError.GetLastErrorString());
  else print("PHASE8 FIXTURE " + what + " x=" + x + " y=" + y);
 }

 /* Straight or diagonal rail from (x0, y0) to (x1, y1), entering from the tile before (x0, y0). */
 function Line(what, bx, by, x0, y0, x1, y1) {
  Report(what, AIRail.BuildRail(Tile(bx, by), Tile(x0, y0), Tile(x1, y1)), x0, y0);
 }

 function Start() {
  AICompany.SetName("3D Catenary");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  /* The electrified railway: the base rail type with catenary. */
  local electric = null;
  foreach (rt, _ in AIRailTypeList()) if (electric == null && AIRail.GetName(rt).find("Electri") != null) electric = rt;
  if (electric == null) { print("PHASE8 FIXTURE electric rail type not found"); while (true) this.Sleep(1000); }
  AIRail.SetCurrentRailType(electric);
  AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local centre = AITown.GetLocation(towns.Begin());
  local cx = AIMap.GetTileX(centre), cy = AIMap.GetTileY(centre);
  print("PHASE8 FIXTURE town=" + AITown.GetName(towns.Begin()) + " x=" + cx + " y=" + cy + " railtype=" + AIRail.GetName(electric));

  local self = this;
  local site = Spiral(cx, cy, 6, 50, function(t) : (self) { return self.Buildable(t, 26, 16); });
  if (site == null) { print("PHASE8 FIXTURE site failed"); while (true) this.Sleep(1000); }
  local sx = AIMap.GetTileX(site), sy = AIMap.GetTileY(site);
  /* No flat site that large near the town: level one. */
  AITile.LevelTiles(site, Tile(sx + 26, sy + 16));
  if (!FlatArea(site, 26, 16)) print("PHASE8 FIXTURE site not level: " + AIError.GetLastErrorString());
  print("PHASE8 FIXTURE site x=" + sx + " y=" + sy);

  /* Raised block x 15..18, y 1..5: the X line climbs over it and the tunnel runs under it. */
  for (local x = sx + 15; x <= sx + 18; x++) for (local y = sy + 1; y <= sy + 5; y++) AITile.RaiseTile(Tile(x, y), AITile.SLOPE_ELEVATED);

  Line("x_line", sx, sy + 3, sx + 1, sy + 3, sx + 20, sy + 3);
  Line("y_line", sx + 5, sy, sx + 5, sy + 1, sx + 5, sy + 13);
  Report("crossing", AIRoad.BuildRoad(Tile(sx + 2, sy + 11), Tile(sx + 8, sy + 11)), sx + 5, sy + 11);
  Line("diagonal", sx + 17, sy + 8, sx + 18, sy + 8, sx + 24, sy + 14);

  /* Station: two platforms of 4 along X with track beyond both ends and a depot facing it. */
  Report("station", AIRail.BuildRailStation(Tile(sx + 8, sy + 8), AIRail.RAILTRACK_NE_SW, 2, 4, AIStation.STATION_NEW), sx + 8, sy + 8);
  foreach (y in [sy + 8, sy + 9]) {
   Line("station_west y=" + y, sx + 8, y, sx + 7, y, sx + 6, y);
   Line("station_east y=" + y, sx + 11, y, sx + 12, y, sx + 14, y);
  }
  local depot = Tile(sx + 15, sy + 8);
  Report("depot", AIRail.BuildRailDepot(depot, Tile(sx + 14, sy + 8)), sx + 15, sy + 8);
  Line("depot_track", sx + 15, sy + 8, sx + 14, sy + 8, sx + 13, sy + 8);

  /* Tunnel along Y through the raised block, with track at its south end. */
  local portal = Tile(sx + 16, sy);
  local tunnel = AITunnel.BuildTunnel(AIVehicle.VT_RAIL, portal);
  Report("tunnel", tunnel, sx + 16, sy);
  if (tunnel) {
   local other = AITunnel.GetOtherTunnelEnd(portal);
   local ox = AIMap.GetTileX(other), oy = AIMap.GetTileY(other);
   Line("tunnel_track", ox, oy, ox, oy + 1, ox, oy + 2);
  }

  /* Rail bridge along Y on flat land, with track at both ends. */
  Report("bridge", AIBridge.BuildBridge(AIVehicle.VT_RAIL, 2, Tile(sx + 23, sy + 1), Tile(sx + 23, sy + 6)), sx + 23, sy + 1);
  foreach (y in [sy, sy + 7]) Report("bridge_track", AIRail.BuildRailTrack(Tile(sx + 23, y), AIRail.RAILTRACK_NW_SE), sx + 23, y);

  /* An electric locomotive leaving the depot, to check the wire clears its pantographs. */
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsWagon);
  engines.KeepValue(0);
  engines.Valuate(AIEngine.GetRailType);
  engines.KeepValue(electric);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  if (engines.IsEmpty()) {
   print("PHASE8 FIXTURE train failed: no electric engine");
  } else {
   local train = AIVehicle.BuildVehicle(depot, engines.Begin());
   AIOrder.AppendOrder(train, Tile(sx + 8, sy + 8), AIOrder.OF_NON_STOP_INTERMEDIATE);
   Report("train engine=" + AIEngine.GetName(engines.Begin()), AIVehicle.IsValidVehicle(train) && AIVehicle.StartStopVehicle(train), sx + 15, sy + 8);
   /* Stop it on the open track east of the station, under the wire, for the clearance shots. */
   for (local i = 0; i < 2000; i++) {
    local at = AIVehicle.GetLocation(train);
    if (at == Tile(sx + 13, sy + 8) && AIVehicle.GetState(train) == AIVehicle.VS_RUNNING) {
     AIVehicle.StartStopVehicle(train);
     print("PHASE8 FIXTURE train stopped x=" + AIMap.GetTileX(at) + " y=" + AIMap.GetTileY(at));
     break;
    }
    this.Sleep(1);
   }
  }
  print("PHASE8 FIXTURE done money=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  while (true) this.Sleep(1000);
 }
}
