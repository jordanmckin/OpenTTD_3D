/* OpenTTD Phase 9.5 fixture, GPL-2.0-only. Ordinary AI commands only: a city airport, a small country airfield and a
 * heliport near the largest towns; three small planes between the city and the airfield, which is too small for them
 * all at once so they hold, and two helicopters between the heliport and the city. */
class Air3DFixture extends AIController {
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

 function Check(ok, label) {
  print("PHASE95 " + label + "=" + ok + " error=" + AIError.GetLastErrorString());
  if (!ok) throw "Fixture failed: " + label;
 }

 /* An airport of this type near the first of the towns, in order, with room for it. */
 function Airport(towns, type, label) {
  local w = AIAirport.GetAirportWidth(type), h = AIAirport.GetAirportHeight(type);
  foreach (town in towns) {
   local at = AITown.GetLocation(town);
   local tile = Spiral(AIMap.GetTileX(at), AIMap.GetTileY(at), 4, 24, function(t) : (type, w, h) {
    return AITile.IsBuildableRectangle(t, w, h) && AIAirport.BuildAirport(t, type, AIStation.STATION_NEW);
   });
   if (tile != null) {
    print("PHASE95 AIRPORT " + label + " x=" + AIMap.GetTileX(tile) + " y=" + AIMap.GetTileY(tile));
    return tile;
   }
  }
  Check(false, label + " airport");
 }

 function Aircraft(plane_type, hangar, a, b, label) {
  local engines = AIEngineList(AIVehicle.VT_AIR);
  engines.Valuate(AIEngine.GetPlaneType);
  engines.KeepValue(plane_type);
  engines.Valuate(AIEngine.IsBuildable);
  engines.KeepValue(1);
  Check(!engines.IsEmpty(), label + " engine");
  local v = AIVehicle.BuildVehicle(hangar, engines.Begin());
  Check(AIVehicle.IsValidVehicle(v), label);
  Check(AIOrder.AppendOrder(v, a, AIOrder.OF_NONE), label + " first order");
  Check(AIOrder.AppendOrder(v, b, AIOrder.OF_NONE), label + " second order");
  Check(AIVehicle.StartStopVehicle(v), label + " start");
  print("PHASE95 AIRCRAFT " + label + " id=" + v);
  return v;
 }

 function Start() {
  AICompany.SetName("3D Air");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local list = AITownList();
  list.Valuate(AITown.GetPopulation);
  list.Sort(AIList.SORT_BY_VALUE, false);
  local towns = [];
  foreach (town, _ in list) towns.append(town);
  local from = function(k) : (towns) { local r = []; for (local i = 0; i < towns.len(); i++) r.append(towns[(i + k) % towns.len()]); return r; };
  local city = Airport(towns, AIAirport.AT_LARGE, "city");
  local country = Airport(from(1), AIAirport.AT_SMALL, "country");
  local heliport = Airport(from(2), AIAirport.AT_HELIPORT, "heliport");
  local hangar = AIAirport.GetHangarOfAirport(city);
  /* Spaced out, so they reach the airfield together only now and then. */
  for (local i = 0; i < 3; i++) {
   Aircraft(AIAirport.PT_SMALL_PLANE, hangar, i == 1 ? city : country, i == 1 ? country : city, "plane" + i);
   this.Sleep(150);
  }
  for (local i = 0; i < 2; i++) {
   Aircraft(AIAirport.PT_HELICOPTER, hangar, i == 0 ? heliport : city, i == 0 ? city : heliport, "helicopter" + i);
   this.Sleep(150);
  }
  print("PHASE95 FIXTURE done");
  while (true) this.Sleep(1000);
 }
}
