/* OpenTTD Phase 8.7 fixture, GPL-2.0-only: everything that shows an effect or a moving industry part, through ordinary
 * commands. Near the largest town: a power station (chimney smoke, transformer sparks), a coal mine (headframe wheel) and
 * oil wells (pumps); near the map edge an oil refinery and, on the sea, an oil rig (flare flames). On a levelled site,
 * three electrified lines each run a steam, a diesel and an electric train between two stations (smoke, sparks; the
 * game is set to break vehicles down often), and a fourth line has two trains driven at each other near the end of a
 * month (explosions, crash smoke). The town's roads are rebuilt (roadworks bulldozers). */
class Effects3DFixture extends AIController {
 function Abs(v) { return v < 0 ? -v : v; }
 function Tile(x, y) { return AIMap.GetTileIndex(x, y); }

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

 function Buildable(t, w, h) {
  local x0 = AIMap.GetTileX(t), y0 = AIMap.GetTileY(t);
  for (local x = x0; x < x0 + w; x++) for (local y = y0; y < y0 + h; y++) {
   local u = Tile(x, y);
   if (!AIMap.IsValidTile(u) || !AITile.IsBuildable(u)) return false;
  }
  /* Two tiles clear of the sea and its coast all round: levelled land beside them floods. */
  for (local x = x0 - 2; x < x0 + w + 2; x++) for (local y = y0 - 2; y < y0 + h + 2; y++) {
   local u = Tile(x, y);
   if (!AIMap.IsValidTile(u) || AITile.IsWaterTile(u) || AITile.IsCoastTile(u)) return false;
  }
  return true;
 }

 function Report(what, ok, tile) {
  if (!ok) print("PHASE8 FIXTURE " + what + " failed: " + AIError.GetLastErrorString());
  else print("PHASE8 FIXTURE " + what + " x=" + AIMap.GetTileX(tile) + " y=" + AIMap.GetTileY(tile));
  return ok;
 }

 site_x = 0; site_y = 0;
 CRASH_TRAVEL = 125; ///< Ticks from restarting the crash trains to their collision (logged as travel=).

 /* An industry from t (up to 5 x 5 tiles) stays off the railway site and a one-tile margin round it. */
 function ClearOfSite(t) {
  local x = AIMap.GetTileX(t), y = AIMap.GetTileY(t);
  return x + 5 < site_x - 1 || x > site_x + 25 || y + 5 < site_y - 1 || y > site_y + 10;
 }

 function IndustryType(name) {
  foreach (t, _ in AIIndustryTypeList()) if (AIIndustryType.GetName(t) == name) return t;
  return null;
 }

 /* Fund an industry on the first tile round (cx, cy) where the game allows it, clear of the railway site:
  * funding an industry clears the company's own track under it. */
 function Fund(name, cx, cy, r0, r1) {
  local type = IndustryType(name);
  if (type == null) { print("PHASE8 FIXTURE " + name + " failed: no such type"); return null; }
  local self = this;
  local tile = Spiral(cx, cy, r0, r1, function(t) : (type, self) { return self.ClearOfSite(t) && AIIndustryType.BuildIndustry(type, t); });
  Report(name, tile != null, tile);
  return tile;
 }

 /* The first buildable engine whose name has `what` (Steam, Diesel, Electric) that runs on rail type rt. */
 function Engine(what, rt) {
  local engines = AIEngineList(AIVehicle.VT_RAIL);
  engines.Valuate(AIEngine.IsWagon);
  engines.KeepValue(0);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  foreach (e, _ in engines) if (AIEngine.GetName(e).find(what) != null && AIEngine.CanRunOnRail(e, rt)) return e;
  return null;
 }

 function Train(what, rt, depot) {
  local e = Engine(what, rt);
  if (e == null) { print("PHASE8 FIXTURE " + what + " train failed: no engine"); return null; }
  local v = AIVehicle.BuildVehicle(depot, e);
  if (!AIVehicle.IsValidVehicle(v)) {
   print("PHASE8 FIXTURE " + what + " train failed: " + AIError.GetLastErrorString() + " depot=" + AIRail.IsRailDepotTile(depot) + " owned=" + AITile.GetOwner(depot) + " engine=" + AIEngine.GetName(e) + " money=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
   return null;
  }
  print("PHASE8 FIXTURE " + what + " train engine=" + AIEngine.GetName(e));
  return v;
 }

 function Start() {
  AICompany.SetName("3D Effects");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local electric = null;
  foreach (rt, _ in AIRailTypeList()) if (electric == null && AIRail.GetName(rt).find("Electri") != null) electric = rt;
  AIRail.SetCurrentRailType(electric);
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local town = towns.Begin();
  local centre = AITown.GetLocation(town);
  local cx = AIMap.GetTileX(centre), cy = AIMap.GetTileY(centre);
  print("PHASE8 FIXTURE town=" + AITown.GetName(town) + " x=" + cx + " y=" + cy);

  /* Railway site: 24 x 9 tiles, levelled, nearest the map centre (the largest town may be on the coast).
   * Lines along X at rows 1, 3, 5 (service) and 7 (crash). */
  local self = this;
  local site = Spiral(AIMap.GetMapSizeX() / 2, AIMap.GetMapSizeY() / 2, 0, 60, function(t) : (self) { return self.Buildable(t, 24, 9); });
  if (site == null) { print("PHASE8 FIXTURE site failed"); while (true) this.Sleep(1000); }
  local sx = AIMap.GetTileX(site), sy = AIMap.GetTileY(site);
  AITile.LevelTiles(site, Tile(sx + 24, sy + 9));
  print("PHASE8 FIXTURE site x=" + sx + " y=" + sy);
  site_x = sx; site_y = sy;
  foreach (k, what in ["Steam", "Diesel", "Electric"]) {
   local y = sy + 1 + 2 * k;
   local a = Tile(sx + 2, y), b = Tile(sx + 19, y);
   Report("line " + what, AIRail.BuildRailStation(a, AIRail.RAILTRACK_NE_SW, 1, 3, AIStation.STATION_NEW) &&
    AIRail.BuildRailStation(b, AIRail.RAILTRACK_NE_SW, 1, 3, AIStation.STATION_NEW) &&
    AIRail.BuildRail(Tile(sx + 4, y), Tile(sx + 5, y), Tile(sx + 19, y)) /* the last tile is exclusive */, a);
   local depot = Tile(sx + 1, y);
   Report("depot " + what, AIRail.BuildRailDepot(depot, a), depot);
   local v = Train(what, electric, depot);
   if (v == null) continue;
   AIOrder.AppendOrder(v, a, AIOrder.OF_NON_STOP_INTERMEDIATE);
   AIOrder.AppendOrder(v, b, AIOrder.OF_NON_STOP_INTERMEDIATE);
   AIVehicle.StartStopVehicle(v);
  }

  /* Crash line: depot, track, station W, track | gap | track, station E, track, depot. The gap keeps each train in its
   * own block (trains wait in a depot while the block ahead is occupied); each shuttles on its half until it closes. */
  local y = sy + 7;
  local gap = Tile(sx + 11, y);
  local ok = AIRail.BuildRailStation(Tile(sx + 3, y), AIRail.RAILTRACK_NE_SW, 1, 2, AIStation.STATION_NEW) &&
   AIRail.BuildRailStation(Tile(sx + 18, y), AIRail.RAILTRACK_NE_SW, 1, 2, AIStation.STATION_NEW);
  foreach (x in [2, 5, 6, 7, 8, 9, 10, 12, 13, 14, 15, 16, 17, 20, 21]) ok = ok && AIRail.BuildRailTrack(Tile(sx + x, y), AIRail.RAILTRACK_NE_SW);
  Report("crash line", ok, Tile(sx + 2, y));
  local west = Tile(sx + 1, y), east = Tile(sx + 22, y);
  Report("crash depots", AIRail.BuildRailDepot(west, Tile(sx + 2, y)) && AIRail.BuildRailDepot(east, Tile(sx + 21, y)), west);
  local crash = [];
  foreach (pair in [[west, Tile(sx + 3, y), Tile(sx + 18, y)], [east, Tile(sx + 18, y), Tile(sx + 3, y)]]) {
   local v = Train("Diesel", electric, pair[0]);
   if (v == null) continue;
   /* Wagons: a crashed train throws small explosions from random vehicles of the chain. */
   local wagons = AIEngineList(AIVehicle.VT_RAIL);
   wagons.Valuate(AIEngine.IsWagon);
   wagons.KeepValue(1);
   wagons.Valuate(AIEngine.IsBuildable);
   wagons.KeepValue(1);
   for (local k = 0; k < 4 && !wagons.IsEmpty(); k++) {
    local w = AIVehicle.BuildVehicle(pair[0], wagons.Begin());
    if (AIVehicle.IsValidVehicle(w)) AIVehicle.MoveWagon(w, 0, v, 0);
   }
   AIOrder.AppendOrder(v, pair[1], AIOrder.OF_NON_STOP_INTERMEDIATE);
   AIOrder.AppendOrder(v, pair[2], AIOrder.OF_NON_STOP_INTERMEDIATE);
   AIVehicle.StartStopVehicle(v);
   crash.append(v);
  }

  /* Industries: generator side near the town, oil at the map edge (the refinery limit) and on the sea. */
  Fund("Power Station", sx + 4, sy + 13, 0, 30);
  Fund("Coal Mine", sx + 14, sy + 13, 0, 30);
  Fund("Oil Wells", sx - 6, sy + 4, 0, 30);
  local mx = AIMap.GetMapSizeX(), my = AIMap.GetMapSizeY();
  local edge = function(t) : (mx, my) { local x = AIMap.GetTileX(t), y = AIMap.GetTileY(t); return x < 20 || y < 20 || x > mx - 20 || y > my - 20; };
  local refinery = IndustryType("Oil Refinery"), rig = IndustryType("Oil Rig");
  local rt = Spiral(cx, cy, 0, 120, function(t) : (edge, refinery) { return edge(t) && AIIndustryType.BuildIndustry(refinery, t); });
  Report("Oil Refinery", rt != null, rt);
  local gt = Spiral(cx, cy, 0, 120, function(t) : (edge, rig) { return edge(t) && AITile.IsSeaTile(t) && AIIndustryType.BuildIndustry(rig, t); });
  Report("Oil Rig", gt != null, gt);

  Report("roadworks", AITown.PerformTownAction(town, AITown.TOWN_ACTION_ROAD_REBUILD), centre);
  print("PHASE8 FIXTURE built money=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));

  /* Crash, timed for the screenshot at the first month boundary (1 February): stop both trains, close the gap, and
   * restart them CRASH_TRAVEL ticks (measured, as the run is deterministic) plus a margin before the boundary, so the
   * large explosion (64 ticks from the 4th tick of the crash) is on screen then. */
  /* Each train is stopped on its half while heading for the gap (the west one going east from sx + 6, the east one
   * going west from sx + 16) and given the far station, so a restart sends both into the closed gap. */
  while (AIDate.GetDayOfMonth(AIDate.GetCurrentDate()) < 20) this.Sleep(1);
  local stopx = [sx + 6, sx + 16], step = [1, -1], last = [-1, -1], held = [false, false];
  while (!(held[0] && held[1])) {
   foreach (i, v in crash) {
    if (held[i]) continue;
    local x = AIMap.GetTileX(AIVehicle.GetLocation(v));
    if (x == stopx[i] && last[i] == x - step[i] && AIVehicle.GetState(v) == AIVehicle.VS_RUNNING) {
     AIVehicle.StartStopVehicle(v);
     AIOrder.SkipToOrder(v, 1);
     held[i] = true;
    }
    if (x != last[i]) last[i] = x;
   }
   this.Sleep(1);
  }
  foreach (v in crash) while (AIVehicle.GetCurrentSpeed(v) > 0) this.Sleep(1);
  Report("crash gap closed", AIRail.BuildRailTrack(gap, AIRail.RAILTRACK_NE_SW), gap);
  while (AIDate.GetDayOfMonth(AIDate.GetCurrentDate()) != 30) this.Sleep(1);
  local boundary = this.GetTick() + 2 * 74; // a day is 74 ticks; the AI runs every tick, so this is the first tick of the 30th
  while (this.GetTick() < boundary - CRASH_TRAVEL - 30) this.Sleep(1);
  local started = this.GetTick();
  foreach (v in crash) AIVehicle.StartStopVehicle(v);
  print("PHASE8 FIXTURE crash started day=" + AIDate.GetDayOfMonth(AIDate.GetCurrentDate()) + " boundary_in=" + (boundary - started));
  local tick = 0;
  while (true) {
   if (tick++ % 20 == 0 && tick < 2000) foreach (v in crash) print("PHASE8 FIXTURE crash train state=" + AIVehicle.GetState(v) + " x=" + AIMap.GetTileX(AIVehicle.GetLocation(v)) + " y=" + AIMap.GetTileY(AIVehicle.GetLocation(v)));
   foreach (v in crash) {
    if (AIVehicle.IsValidVehicle(v) && AIVehicle.GetState(v) == AIVehicle.VS_CRASHED) {
     local d = AIDate.GetCurrentDate();
     print("PHASE8 FIXTURE crashed month=" + AIDate.GetMonth(d) + " day=" + AIDate.GetDayOfMonth(d) + " travel=" + (this.GetTick() - started) + " x=" + AIMap.GetTileX(AIVehicle.GetLocation(v)) + " y=" + AIMap.GetTileY(AIVehicle.GetLocation(v)));
     while (true) this.Sleep(1000);
    }
   }
   this.Sleep(1);
  }
 }
}
