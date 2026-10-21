/* OpenTTD Phase 9.5 fixture, GPL-2.0-only. Loaded by the Phase 4 fixture AI after a reload; ordinary AI commands only.
 * A straight dead-end road with a stop near each end: two trucks run between the stops and turn round at the road
 * ends, and once the first truck stops on the straight the second overtakes it. */
function Phase95Edges(ai)
{
 local T = function(x, y) { return AIMap.GetTileIndex(x, y); };
 local y = 52, x0 = 10, x1 = 54;
 for (local x = x0 - 1; x <= x1 + 1; x++) for (local yy = y - 1; yy <= y + 2; yy++) {
  local t = T(x, yy);
  if (!AITile.IsBuildable(t) && !AIRoad.IsRoadTile(t)) AITile.DemolishTile(t);
 }
 ai.Check(AITile.LevelTiles(T(x0 - 1, y - 1), T(x1 + 1, y + 2)), "edges level");
 AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
 ai.Check(AIRoad.BuildRoad(T(x0, y), T(x1, y)), "edges road");
 ai.Check(AIRoad.BuildRoadDepot(T(x0 + 2, y + 1), T(x0 + 2, y)), "edges depot");
 ai.Check(AIRoad.BuildRoad(T(x0 + 2, y + 1), T(x0 + 2, y)), "edges depot connection");
 ai.Check(AIRoad.BuildDriveThroughRoadStation(T(x0 + 5, y), T(x0 + 6, y), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "edges west stop");
 ai.Check(AIRoad.BuildDriveThroughRoadStation(T(x1 - 5, y), T(x1 - 6, y), AIRoad.ROADVEHTYPE_TRUCK, AIStation.STATION_NEW), "edges east stop");
 local engine = AIVehicle.GetEngineType(ai.truck_id);
 local trucks = [];
 for (local i = 0; i < 2; i++) {
  local v = AIVehicle.BuildVehicle(T(x0 + 2, y + 1), engine);
  ai.Check(AIVehicle.IsValidVehicle(v), "edges truck");
  ai.Check(AIOrder.AppendOrder(v, T(x0 + 5, y), AIOrder.OF_NON_STOP_INTERMEDIATE), "edges truck west order");
  ai.Check(AIOrder.AppendOrder(v, T(x1 - 5, y), AIOrder.OF_NON_STOP_INTERMEDIATE), "edges truck east order");
  trucks.append(v);
  print("PHASE95 TRUCK id=" + v);
 }
 ai.Check(AIVehicle.StartStopVehicle(trucks[0]), "edges first truck start");
 /* The trucks turn round at the road ends for a while first, so the test script can ride with them. */
 local start = AIDate.GetCurrentDate();
 while (AIDate.GetCurrentDate() < start + 4) ai.Sleep(1);
 ai.Check(AIVehicle.StartStopVehicle(trucks[1]), "edges second truck start");
 while (AIDate.GetCurrentDate() < start + 40) ai.Sleep(1);
 /* The first truck stops halfway along, heading east with the second behind it, which then overtakes. */
 local X = function(v) { return AIMap.GetTileX(AIVehicle.GetLocation(v)); };
 for (local tries = 0; ; tries++) {
  local a = X(trucks[0]), b = X(trucks[1]);
  ai.Sleep(30);
  local a2 = X(trucks[0]), b2 = X(trucks[1]);
  if (a2 >= 26 && a2 <= 34 && a2 > a && b2 > b && b2 < a2 - 2 && b2 > x0 + 6) break;
  if (tries > 2000) throw "Fixture failed: no overtaking set-up";
 }
 ai.Check(AIVehicle.StartStopVehicle(trucks[0]), "edges first truck stop");
 print("PHASE95 STOPPED truck=" + trucks[0] + " date=" + AIDate.GetCurrentDate());
 for (local tries = 0; AIMap.GetTileX(AIVehicle.GetLocation(trucks[1])) <= AIMap.GetTileX(AIVehicle.GetLocation(trucks[0])) + 1; tries++) {
  ai.Sleep(1);
  if (tries > 5000) throw "Fixture failed: no overtaking";
 }
 print("PHASE95 OVERTAKEN truck=" + trucks[1] + " date=" + AIDate.GetCurrentDate());
 ai.Sleep(74);
 ai.Check(AIVehicle.StartStopVehicle(trucks[0]), "edges first truck restart");
}
