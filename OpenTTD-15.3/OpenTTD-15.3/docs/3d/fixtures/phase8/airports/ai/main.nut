/* OpenTTD Phase 8.6 fixture, GPL-2.0-only: every original airport type, cheapest first, near the
 * largest towns (the fixture's council is permissive), and an aircraft at the city airport. */
class Airports3DFixture extends AIController {
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
  AICompany.SetName("3D Airports");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local centre = AITown.GetLocation(towns.Begin());
  local cx = AIMap.GetTileX(centre), cy = AIMap.GetTileY(centre);
  print("PHASE8 FIXTURE town=" + AITown.GetName(towns.Begin()) + " x=" + cx + " y=" + cy);
  local types = [["city", AIAirport.AT_LARGE], ["country", AIAirport.AT_SMALL], ["commuter", AIAirport.AT_COMMUTER],
   ["helistation", AIAirport.AT_HELISTATION], ["helidepot", AIAirport.AT_HELIDEPOT], ["heliport", AIAirport.AT_HELIPORT],
   ["metropolitan", AIAirport.AT_METROPOLITAN], ["international", AIAirport.AT_INTERNATIONAL],
   ["intercontinental", AIAirport.AT_INTERCON]];
  local city = null;
  foreach (a in types) {
   local type = a[1];
   local w = AIAirport.GetAirportWidth(type), h = AIAirport.GetAirportHeight(type);
   local tile = null;
   for (local town = towns.Begin(); tile == null && !towns.IsEnd(); town = towns.Next()) {
    local at = AITown.GetLocation(town);
    tile = Spiral(AIMap.GetTileX(at), AIMap.GetTileY(at), 4, 24, function(t) : (type, w, h) {
     return AITile.IsBuildableRectangle(t, w, h) && AIAirport.BuildAirport(t, type, AIStation.STATION_NEW);
    });
   }
   Report("airport_" + a[0], tile);
   if (tile == null) print("PHASE8 FIXTURE last error " + AIError.GetLastErrorString() + " money=" + AICompany.GetBankBalance(AICompany.COMPANY_SELF));
   if (a[0] == "city") city = tile;
  }
  /* An aircraft at the city airport shows the stands, runway and hangar in use. */
  if (city != null) {
   local engines = AIEngineList(AIVehicle.VT_AIR);
   engines.Valuate(AIEngine.GetPlaneType);
   engines.KeepValue(AIAirport.PT_BIG_PLANE);
   if (!engines.IsEmpty()) {
    local v = AIVehicle.BuildVehicle(AIAirport.GetHangarOfAirport(city), engines.Begin());
    if (AIVehicle.IsValidVehicle(v)) {
     AIOrder.AppendOrder(v, city, AIOrder.OF_NONE);
     AIVehicle.StartStopVehicle(v);
    }
   }
  }
  print("PHASE8 FIXTURE done");
  while (true) this.Sleep(1000);
 }
}
