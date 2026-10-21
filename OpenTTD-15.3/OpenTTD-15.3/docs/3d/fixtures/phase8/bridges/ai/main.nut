/* OpenTTD Phase 8.6 fixture, GPL-2.0-only: every original bridge type through ordinary commands, near the largest
 * town. Rail bridges along X on flat land (lengths that use every middle piece), road bridges along Y, a raised
 * site with valley bridges between two plateaus (heads on slopes) and rail and road tunnels, and a bridge over rail. */
class Bridges3DFixture extends AIController {
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

 function Report(what, a, b) {
  if (a == null) print("PHASE8 FIXTURE " + what + " failed: " + AIError.GetLastErrorString());
  else print("PHASE8 FIXTURE " + what + " x=" + AIMap.GetTileX(a) + " y=" + AIMap.GetTileY(a) + " to x=" + AIMap.GetTileX(b) + " y=" + AIMap.GetTileY(b));
 }

 /* A bridge of n tiles including its heads on flat land, with a free row on either side; axis 0 = X, 1 = Y. */
 function FlatBridge(cx, cy, vt, type, n, axis, what) {
  local self = this, built = null;
  local found = Spiral(cx, cy, 4, 40, function(t) : (self, vt, type, n, axis) {
   local w = axis == 0 ? n : 3, h = axis == 0 ? 3 : n;
   local x = AIMap.GetTileX(t), y = AIMap.GetTileY(t);
   if (!self.FlatArea(t, w, h)) return false;
   local a = axis == 0 ? self.Tile(x, y + 1) : self.Tile(x + 1, y);
   local b = axis == 0 ? self.Tile(x + n - 1, y + 1) : self.Tile(x + 1, y + n - 1);
   return AIBridge.BuildBridge(vt, type, a, b);
  });
  if (found == null) { Report(what, null, null); return; }
  local x = AIMap.GetTileX(found), y = AIMap.GetTileY(found);
  local a = axis == 0 ? Tile(x, y + 1) : Tile(x + 1, y);
  Report(what, a, AIBridge.GetOtherBridgeEnd(a));
 }

 function Start() {
  AICompany.SetName("3D Bridges");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local rails = AIRailTypeList();
  AIRail.SetCurrentRailType(rails.Begin());
  AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local centre = AITown.GetLocation(towns.Begin());
  local cx = AIMap.GetTileX(centre), cy = AIMap.GetTileY(centre);
  print("PHASE8 FIXTURE town=" + AITown.GetName(towns.Begin()) + " x=" + cx + " y=" + cy);

  /* Raised site first, it needs the largest flat area: plateaus A (x 0..3) and B (x 10..13), rows 0..5. */
  local self = this;
  local site = Spiral(cx, cy, 6, 40, function(t) : (self) { return self.FlatArea(t, 22, 12); });
  if (site != null) {
   local sx = AIMap.GetTileX(site) + 2, sy = AIMap.GetTileY(site) + 3;
   foreach (x0 in [sx, sx + 10]) for (local x = x0; x < x0 + 4; x++) for (local y = sy; y < sy + 6; y++) AITile.RaiseTile(Tile(x, y), AITile.SLOPE_ELEVATED);
   print("PHASE8 FIXTURE site x=" + sx + " y=" + sy);
   /* Valley bridges between the slope tiles beside each plateau: heads on inclined slopes, deck one level up. */
   local valley = [[0, sy + 0], [4, sy + 2], [6, sy + 4], [10, sy + 5]];
   foreach (v in valley) {
    local a = Tile(sx + 4, v[1]), b = Tile(sx + 9, v[1]);
    Report("valley_bridge type=" + v[0], AIBridge.BuildBridge(AIVehicle.VT_RAIL, v[0], a, b) ? a : null, b);
   }
   /* Tunnels through plateau A along Y, rail and road. */
   foreach (k, vt in [AIVehicle.VT_RAIL, AIVehicle.VT_ROAD]) {
    local t = Tile(sx + 1 + k, sy - 1);
    Report("tunnel vt=" + vt, AITunnel.BuildTunnel(vt, t) ? t : null, AITunnel.GetOtherTunnelEnd(t));
   }
   /* A rail bridge over a railway along Y: the pillars stay clear of the track. */
   local r0 = Tile(sx + 17, sy - 2), r1 = Tile(sx + 17, sy + 8);
   AIRail.BuildRail(Tile(sx + 17, sy - 3), r0, r1);
   local a = Tile(sx + 15, sy + 7), b = Tile(sx + 19, sy + 7);
   Report("over_rail_bridge type=2", AIBridge.BuildBridge(AIVehicle.VT_RAIL, 2, a, b) ? a : null, b);
  } else {
   print("PHASE8 FIXTURE site failed");
  }

  /* Every type as a rail bridge along X: 7 tiles (N, IN, ME, IS, S) or the longest allowed. */
  for (local type = 0; type < 13; type++) {
   local n = 7;
   if (n > AIBridge.GetMaxLength(type)) n = AIBridge.GetMaxLength(type);
   FlatBridge(cx, cy, AIVehicle.VT_RAIL, type, n, 0, "rail_bridge type=" + type + " n=" + n);
  }
  /* Length 5 (N, MO, S) where the type draws a middle-odd piece. */
  foreach (type in [3, 4, 5]) FlatBridge(cx, cy, AIVehicle.VT_RAIL, type, 5, 0, "rail_bridge type=" + type + " n=5");
  /* Road bridges along Y. */
  foreach (type in [0, 2, 4, 7, 11]) FlatBridge(cx, cy, AIVehicle.VT_ROAD, type, 6, 1, "road_bridge type=" + type + " n=6");
  print("PHASE8 FIXTURE done money=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
  while (true) this.Sleep(1000);
 }
}
