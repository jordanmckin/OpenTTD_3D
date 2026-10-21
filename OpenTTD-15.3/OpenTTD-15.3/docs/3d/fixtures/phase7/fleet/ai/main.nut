/* OpenTTD Phase 7 fleet fixture, GPL-2.0-only. No rendering callbacks or direct simulation writes.
 * Buses run between two drive-through stops in each of the towns nearest the map centre;
 * shuttle trains run on straight lines near the centre. A service that cannot be placed is
 * skipped, and the fixture only requires a minimum total fleet. */
class Fleet3DFixture extends AIController {
 built = false;
 static TOWNS = 12;
 static BUSES_PER_TOWN = 24;
 static RAIL_LINES = 12;
 static RAIL_LENGTH = 40;
 static WAGONS = 4;
 static MIN_VEHICLES = 200;

 function Save() { return {built=built}; }
 function Load(version,data) { this.built=("built" in data)?data.built:false; }
 function Tile(x,y) { return AIMap.GetTileIndex(x,y); }
 function Check(ok,label) {
  if (!ok) { print("PHASE7 " + label + "=false error=" + AIError.GetLastErrorString()); throw "Fixture failed: " + label; }
 }

 function Passengers() {
  foreach (id,v in AICargoList()) if (AICargo.HasCargoClass(id,AICargo.CC_PASSENGERS)) return id;
  return -1;
 }
 function Cheapest(list) {
  list.Valuate(AIEngine.GetPrice); list.Sort(AIList.SORT_BY_VALUE,true);
  return list.IsEmpty() ? -1 : list.Begin();
 }

 /* A flat, straight town road tile along one axis with no side connections. */
 function StraightRoad(t,dx,dy) {
  local a=t+AIMap.GetTileIndex(dx,dy), b=t-AIMap.GetTileIndex(dx,dy);
  local c=t+AIMap.GetTileIndex(dy,dx), d=t-AIMap.GetTileIndex(dy,dx);
  return AIRoad.IsRoadTile(t) && !AIRoad.IsRoadStationTile(t) && !AIRoad.IsRoadDepotTile(t) && !AIBridge.IsBridgeTile(t) && !AITunnel.IsTunnelTile(t)
   && AITile.GetSlope(t)==AITile.SLOPE_FLAT && !AIRail.IsLevelCrossingTile(t)
   && AIRoad.AreRoadTilesConnected(t,a) && AIRoad.AreRoadTilesConnected(t,b)
   && !AIRoad.AreRoadTilesConnected(t,c) && !AIRoad.AreRoadTilesConnected(t,d);
 }
 function TownStop(town,used) {
  local tiles=AITileList();
  local centre=AITown.GetLocation(town);
  tiles.AddRectangle(centre-AIMap.GetTileIndex(8,8),centre+AIMap.GetTileIndex(8,8));
  tiles.Valuate(AIMap.DistanceManhattan,centre); tiles.Sort(AIList.SORT_BY_VALUE,true);
  foreach (t,v in tiles) {
   local far=true;
   foreach (u in used) if (AIMap.DistanceManhattan(t,u)<5) far=false;
   if (!far) continue;
   foreach (axis in [[1,0],[0,1]]) {
    if (!StraightRoad(t,axis[0],axis[1])) continue;
    if (AIRoad.BuildDriveThroughRoadStation(t,t+AIMap.GetTileIndex(axis[0],axis[1]),AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW)) return t;
   }
  }
  return null;
 }
 function TownDepot(town) {
  local tiles=AITileList();
  local centre=AITown.GetLocation(town);
  tiles.AddRectangle(centre-AIMap.GetTileIndex(10,10),centre+AIMap.GetTileIndex(10,10));
  tiles.Valuate(AIMap.DistanceManhattan,centre); tiles.Sort(AIList.SORT_BY_VALUE,true);
  foreach (t,v in tiles) {
   if (!AITile.IsBuildable(t) || AITile.GetSlope(t)!=AITile.SLOPE_FLAT) continue;
   foreach (o in [[1,0],[-1,0],[0,1],[0,-1]]) {
    local front=t+AIMap.GetTileIndex(o[0],o[1]);
    if (!AIRoad.IsRoadTile(front) || AIRoad.IsRoadStationTile(front) || AITile.GetSlope(front)!=AITile.SLOPE_FLAT) continue;
    if (!AIRoad.BuildRoadDepot(t,front)) continue;
    if (AIRoad.BuildRoad(t,front)) return t;
    AIRoad.RemoveRoadDepot(t);
   }
  }
  return null;
 }
 function Buses(engine) {
  local towns=AITownList();
  local mid=Tile(AIMap.GetMapSizeX()/2,AIMap.GetMapSizeY()/2);
  towns.Valuate(AITown.GetDistanceManhattanToTile,mid); towns.Sort(AIList.SORT_BY_VALUE,true);
  print("PHASE7 FLEET towns=" + AITownList().Count());
  local count=0, served=0;
  foreach (town,v in towns) {
   if (served>=TOWNS) break;
   local a=TownStop(town,[]);
   if (a==null) continue;
   local b=TownStop(town,[a]);
   local depot=b==null ? null : TownDepot(town);
   if (depot==null) { print("PHASE7 FLEET skip town=" + AITown.GetName(town)); continue; }
   local first=AIVehicle.BuildVehicle(depot,engine);
   if (!AIVehicle.IsValidVehicle(first)) continue;
   Check(AIOrder.AppendOrder(first,a,AIOrder.OF_NONE),"bus order a");
   Check(AIOrder.AppendOrder(first,b,AIOrder.OF_NONE),"bus order b");
   Check(AIVehicle.StartStopVehicle(first),"bus start");
   count++;
   for (local i=1;i<BUSES_PER_TOWN;i++) {
    local v=AIVehicle.CloneVehicle(depot,first,true);
    if (!AIVehicle.IsValidVehicle(v)) break;
    Check(AIVehicle.StartStopVehicle(v),"bus clone start");
    count++;
    this.Sleep(4);
   }
   served++;
   print("PHASE7 FLEET town=" + AITown.GetName(town) + " x=" + AIMap.GetTileX(AITown.GetLocation(town)) + " y=" + AIMap.GetTileY(AITown.GetLocation(town)) + " buses=" + count);
  }
  return count;
 }

 /* Depot, station, straight line and station along X; one train shuttles between the stations. */
 function RailLine(y,x0,loco,wagon) {
  local len=RAIL_LENGTH;
  if (!AITile.IsBuildableRectangle(Tile(x0,y),len,1)) return 0;
  if (!AITile.LevelTiles(Tile(x0,y),Tile(x0+len,y+1))) return 0;
  if (!AIRail.BuildRailStation(Tile(x0+1,y),AIRail.RAILTRACK_NE_SW,1,5,AIStation.STATION_NEW)) return 0;
  if (!AIRail.BuildRailStation(Tile(x0+len-6,y),AIRail.RAILTRACK_NE_SW,1,5,AIStation.STATION_NEW)) return 0;
  /* The end tile of AIRail.BuildRail is exclusive. */
  if (!AIRail.BuildRail(Tile(x0+5,y),Tile(x0+6,y),Tile(x0+len-6,y))) return 0;
  if (!AIRail.BuildRailDepot(Tile(x0,y),Tile(x0+1,y))) return 0;
  local train=AIVehicle.BuildVehicle(Tile(x0,y),loco);
  if (!AIVehicle.IsValidVehicle(train)) return 0;
  local vehicles=1;
  for (local i=0;i<WAGONS;i++) {
   local w=AIVehicle.BuildVehicle(Tile(x0,y),wagon);
   if (!AIVehicle.IsValidVehicle(w)) break;
   Check(AIVehicle.MoveWagon(w,0,train,AIVehicle.GetNumWagons(train)-1),"attach wagon");
   vehicles++;
  }
  Check(AIOrder.AppendOrder(train,Tile(x0+len-4,y),AIOrder.OF_NONE),"train order east");
  Check(AIOrder.AppendOrder(train,Tile(x0+3,y),AIOrder.OF_NONE),"train order west");
  Check(AIVehicle.StartStopVehicle(train),"train start");
  return vehicles;
 }
 function Trains(passengers) {
  local types=AIRailTypeList();
  if (types.IsEmpty()) return 0;
  AIRail.SetCurrentRailType(types.Begin());
  local locos=AIEngineList(AIVehicle.VT_RAIL);
  locos.Valuate(AIEngine.IsWagon); locos.KeepValue(0);
  locos.Valuate(AIEngine.CanRunOnRail,AIRail.GetCurrentRailType()); locos.KeepValue(1);
  locos.Valuate(AIEngine.IsBuildable); locos.KeepValue(1);
  local wagons=AIEngineList(AIVehicle.VT_RAIL);
  wagons.Valuate(AIEngine.IsWagon); wagons.KeepValue(1);
  wagons.Valuate(AIEngine.CanRefitCargo,passengers); wagons.KeepValue(1);
  wagons.Valuate(AIEngine.CanRunOnRail,AIRail.GetCurrentRailType()); wagons.KeepValue(1);
  local loco=Cheapest(locos), wagon=Cheapest(wagons);
  if (loco<0 || wagon<0) return 0;
  local mx=AIMap.GetMapSizeX()/2, my=AIMap.GetMapSizeY()/2;
  local count=0, lines=0;
  for (local d=0; d<120 && lines<RAIL_LINES; d+=3) foreach (y in [my+d, my-d-2]) {
   if (lines>=RAIL_LINES) break;
   local n=RailLine(y,mx-RAIL_LENGTH/2,loco,wagon);
   if (n>0) { lines++; count+=n; print("PHASE7 FLEET rail y=" + y + " vehicles=" + n); }
  }
  return count;
 }

 function Start() {
  if (built) { print("PHASE7 FLEET_RELOADED"); for (;;) this.Sleep(1000); }
  AICompany.SetName("3D Fleet");
  Check(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"loan");
  AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
  local passengers=Passengers();
  Check(passengers>=0,"passenger cargo");
  local buses=AIEngineList(AIVehicle.VT_ROAD);
  buses.Valuate(AIEngine.GetCargoType); buses.KeepValue(passengers);
  buses.Valuate(AIEngine.IsBuildable); buses.KeepValue(1);
  buses.Valuate(AIEngine.GetRoadType); buses.KeepValue(AIRoad.ROADTYPE_ROAD);
  local bus=Cheapest(buses);
  Check(bus>=0,"bus engine");
  local trains=Trains(passengers);
  local road=Buses(bus);
  Check(road+trains>=MIN_VEHICLES,"minimum fleet");
  built=true;
  print("PHASE7 FLEET_READY vehicles=" + (road+trains) + " buses=" + road + " rail_vehicles=" + trains);
  for (;;) this.Sleep(1000);
 }
}
