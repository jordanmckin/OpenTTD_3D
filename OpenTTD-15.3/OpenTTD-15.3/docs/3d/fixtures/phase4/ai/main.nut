/* OpenTTD Phase 4 fixture, GPL-2.0-only. No rendering callbacks or direct simulation writes. */
class Infrastructure3DFixture extends AIController {
 train_id = null;
 truck_id = null;
 coal_id = null;
 depot_test_done = false;

 function Save() { return {train=train_id,coal=coal_id,truck=truck_id,depot_test_done=depot_test_done}; }
 function Load(version,data) { this.train_id=data.train; this.truck_id=data.truck; this.coal_id=data.coal; this.depot_test_done=("depot_test_done" in data)?data.depot_test_done:false; }
 function Monitor() {
  local samples=0, train_depot=0, truck_depot=0;
  for (;;) {
   samples++;
   if (!depot_test_done && samples==120) {
    Check(AIVehicle.SendVehicleToDepot(train_id),"send train to depot");
    Check(AIVehicle.SendVehicleToDepot(truck_id),"send truck to depot");
    train_depot=1; truck_depot=1;
   }
   if (train_depot==1 && AIVehicle.IsStoppedInDepot(train_id)) {
    print("PHASE4 TRAIN_DEPOT_CONFIRMED"); this.Sleep(30);
    Check(AIVehicle.StartStopVehicle(train_id),"restart train after depot"); train_depot=2;
   }
   if (truck_depot==1 && AIVehicle.IsStoppedInDepot(truck_id)) {
    print("PHASE4 TRUCK_DEPOT_CONFIRMED"); this.Sleep(30);
    Check(AIVehicle.StartStopVehicle(truck_id),"restart truck after depot"); truck_depot=2;
   }
   if (train_depot==2 && truck_depot==2) depot_test_done=true;
   if (!depot_test_done && samples>600) throw "Fixture failed: depot round trip timed out";
   print("PHASE4 RUN tile=" + AIVehicle.GetLocation(train_id) + " load=" + AIVehicle.GetCargoLoad(train_id,coal_id) + " profit=" + AIVehicle.GetProfitThisYear(train_id));
   if (truck_id != null) print("PHASE4 ROAD tile=" + AIVehicle.GetLocation(truck_id) + " speed=" + AIVehicle.GetCurrentSpeed(truck_id));
   this.Sleep(30);
  }
 }
 function Tile(x,y) { return AIMap.GetTileIndex(x,y); }
 function Check(ok,label) {
  print("PHASE4 " + label + "=" + ok + " error=" + AIError.GetLastErrorString());
  if (!ok) throw "Fixture failed: " + label;
 }

 function Bridge(kind,a,b,label) {
  local built=false;
  foreach (id,v in AIBridgeList_Length(AIMap.DistanceManhattan(a,b)+1)) {
   if (AIBridge.BuildBridge(kind,id,a,b)) { built=true; break; }
  }
  Check(built,label);
 }
 function Hill(y) {
  for (local x=33;x<=37;x++) for (local yy=y-2;yy<=y+2;yy++)
   Check(AITile.RaiseTile(Tile(x,yy),AITile.SLOPE_N),"hill corner " + x + "," + yy);
 }
 function Infrastructure() {
  AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
  Hill(29); Hill(38);
  for (local y=21;y<=25;y++) for (local x=52;x<=56;x++)
   Check(AITile.RaiseTile(Tile(x,y),AITile.SLOPE_N),"perpendicular tunnel hill");
  Check(AITunnel.BuildTunnel(AIVehicle.VT_ROAD,Tile(54,20)),"perpendicular road tunnel");
  Check(AITunnel.GetOtherTunnelEnd(Tile(54,20))==Tile(54,25),"perpendicular tunnel exit");
  Check(AITile.RaiseTile(Tile(54,31),AITile.SLOPE_N),"north bridge foundation corner");
  Check(AITile.RaiseTile(Tile(55,36),AITile.SLOPE_N),"south bridge foundation corner");
  Bridge(AIVehicle.VT_ROAD,Tile(54,31),Tile(54,35),"perpendicular road bridge");
  Check(AIRoad.AreRoadTilesConnected(Tile(54,19),Tile(54,20)) || AIRoad.BuildRoad(Tile(54,19),Tile(54,20)),"perpendicular north road");
  Check(AIRoad.BuildRoad(Tile(54,25),Tile(54,31)),"perpendicular middle road");
  Check(AIRoad.BuildRoad(Tile(54,35),Tile(54,38)),"perpendicular south road");
  Check(AIRoad.BuildRoad(Tile(44,38),Tile(54,38)),"perpendicular road link");
  for (local y=28;y<=42;y++) {
   local t=Tile(20,y);
   print("PHASE4 ROAD_SITE y="+y+" buildable="+AITile.IsBuildable(t)+" industry="+AIIndustry.GetIndustryID(t)+" owner="+AITile.GetOwner(t));
   if (!AITile.IsBuildable(t)) Check(AITile.DemolishTile(t),"clear road site " + y);
  }
  Check(AITunnel.BuildTunnel(AIVehicle.VT_RAIL,Tile(32,29)),"rail tunnel");
  Check(AITunnel.GetOtherTunnelEnd(Tile(32,29))==Tile(37,29),"rail tunnel exit");
  Check(AITunnel.RemoveTunnel(Tile(32,29)),"remove rail tunnel");
  Check(AITunnel.BuildTunnel(AIVehicle.VT_RAIL,Tile(32,29)),"rebuild rail tunnel");
  Bridge(AIVehicle.VT_RAIL,Tile(18,29),Tile(22,29),"rail bridge");
  Check(AIBridge.RemoveBridge(Tile(18,29)),"remove rail bridge");
  Bridge(AIVehicle.VT_RAIL,Tile(18,29),Tile(22,29),"rebuild rail bridge");
  for (local y=28;y<42;y++) Check(AIRoad.BuildRoad(Tile(20,y),Tile(20,y+1)),"underpass road y=" + y);
  Bridge(AIVehicle.VT_ROAD,Tile(18,38),Tile(22,38),"road bridge");
  this.Sleep(20);
  Check(AIBridge.RemoveBridge(Tile(18,38)),"remove road bridge");
  this.Sleep(20);
  Bridge(AIVehicle.VT_ROAD,Tile(18,38),Tile(22,38),"rebuild road bridge");
  Check(AITunnel.BuildTunnel(AIVehicle.VT_ROAD,Tile(32,38)),"road tunnel");
  Check(AITunnel.GetOtherTunnelEnd(Tile(32,38))==Tile(37,38),"road tunnel exit");
  this.Sleep(20);
  Check(AITunnel.RemoveTunnel(Tile(32,38)),"remove road tunnel");
  this.Sleep(20);
  Check(AITunnel.BuildTunnel(AIVehicle.VT_ROAD,Tile(32,38)),"rebuild road tunnel");
  Check(AIRoad.BuildRoad(Tile(14,38),Tile(18,38)),"west road");
  Check(AIRoad.BuildRoad(Tile(22,38),Tile(32,38)),"middle road");
  Check(AIRoad.BuildRoad(Tile(37,38),Tile(46,38)),"east road");
  Check(AIRoad.RemoveRoad(Tile(26,38),Tile(27,38)),"remove road segment");
  this.Sleep(20);
  Check(AIRoad.BuildRoad(Tile(26,38),Tile(27,38)),"rebuild road segment");

  Check(AIRoad.BuildRoadDepot(Tile(14,37),Tile(14,38)),"road depot");
  Check(AIRoad.BuildRoad(Tile(14,37),Tile(14,38)),"road depot connection");
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(16,38),Tile(17,38),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"truck west stop");
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(44,38),Tile(45,38),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"truck east stop");
  local engine=-1;
  foreach (id,v in AIEngineList(AIVehicle.VT_ROAD)) {
   if (AICargo.GetCargoLabel(AIEngine.GetCargoType(id))=="COAL") { engine=id; break; }
  }
  Check(engine>=0,"truck identity");
  truck_id=AIVehicle.BuildVehicle(Tile(14,37),engine);
  Check(AIVehicle.IsValidVehicle(truck_id),"truck");
  Check(AIOrder.AppendOrder(truck_id,Tile(16,38),AIOrder.OF_NONE),"truck west order");
  Check(AIOrder.AppendOrder(truck_id,Tile(44,38),AIOrder.OF_NONE),"truck east order");
  Check(AIVehicle.StartStopVehicle(truck_id),"start truck");
 }
 function Start() {
  if (train_id != null && AIVehicle.IsValidVehicle(train_id)) { print("PHASE4 RELOADED train=" + train_id);  Monitor(); }
  AICompany.SetName("3D Infrastructure");
  Check(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"loan");
  AIRail.SetCurrentRailType(0);
  Check(AITile.LevelTiles(Tile(8,18),Tile(57,43)),"level site");
  for (local x=16;x<=17;x++) foreach (y in [29,30,38,39])
   Check(AITile.RaiseTile(Tile(x,y),AITile.SLOPE_N),"sloped approach");
  local mine=-1, power=-1, coal=-1;
  foreach (id,v in AIIndustryTypeList()) {
   local name=AIIndustryType.GetName(id);
   if (name=="Coal Mine") mine=id;
   if (name=="Power Station" || name=="Power Plant") power=id;
  }
  foreach (id,v in AICargoList()) if (AICargo.GetCargoLabel(id)=="COAL") coal=id;
  Check(mine>=0 && power>=0 && coal>=0,"base identities");
  Check(AIIndustryType.BuildIndustry(mine,Tile(10,24)),"coal mine");
  Check(AIIndustryType.BuildIndustry(power,Tile(42,24)),"power station");
  for (local x=10;x<=44;x++) {
   local tile=Tile(x,29);
   print("PHASE4 SITE x=" + x + " buildable=" + AITile.IsBuildable(tile) + " industry=" + AIIndustry.GetIndustryID(tile));
   if (!AITile.IsBuildable(tile)) Check(AITile.DemolishTile(tile),"clear route " + x);
  }
  Check(AIRail.BuildRailStation(Tile(11,29),AIRail.RAILTRACK_NE_SW,1,3,AIStation.STATION_NEW),"mine station");
  Check(AIRail.BuildRailStation(Tile(42,29),AIRail.RAILTRACK_NE_SW,1,3,AIStation.STATION_NEW),"power station platform");
  Infrastructure();
  for (local x=14;x<42;x++) {
   if ((x>=18 && x<=22) || (x>=32 && x<=37)) continue;
   Check(AIRail.BuildRailTrack(Tile(x,29),AIRail.RAILTRACK_NE_SW),"track " + x);
  }
  Check(AIRoad.BuildRoad(Tile(39,28),Tile(39,38)),"live level crossing");
  for (local x=8;x<=28;x+=20) for (local y=8;y<=28;y+=20) print("PHASE4 plant trees=" + AITile.PlantTreeRectangle(Tile(x,y),20,20));
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(54,19),Tile(54,20),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"perpendicular road stop");
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(39,28),Tile(39,29),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"crossing stop");
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(20,28),Tile(20,29),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"underpass north stop");
  Check(AIRoad.BuildDriveThroughRoadStation(Tile(20,42),Tile(20,41),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),"underpass south stop");
  Check(AIRoad.BuildRoadDepot(Tile(19,41),Tile(20,41)),"underpass depot");
  Check(AIRoad.BuildRoad(Tile(19,41),Tile(20,41)),"underpass depot connection");
  local e=AIVehicle.GetEngineType(truck_id);
  foreach (route in [[Tile(14,37),Tile(39,28),Tile(44,38)],[Tile(19,41),Tile(20,28),Tile(20,42)]]) {
   local v=AIVehicle.BuildVehicle(route[0],e);
   Check(AIVehicle.IsValidVehicle(v),"additional truck");
   Check(AIOrder.AppendOrder(v,route[1],AIOrder.OF_NONE),"additional truck first order");
   Check(AIOrder.AppendOrder(v,route[2],AIOrder.OF_NONE),"additional truck second order");
   if (route[0]==Tile(14,37)) Check(AIOrder.AppendOrder(v,Tile(54,19),AIOrder.OF_NONE),"perpendicular truck order");
   Check(AIVehicle.StartStopVehicle(v),"start additional truck");
  }
  Check(AIRail.RemoveRailTrack(Tile(28,29),AIRail.RAILTRACK_NE_SW),"remove rail");
  this.Sleep(80);
  Check(AIRail.BuildRailTrack(Tile(28,29),AIRail.RAILTRACK_NE_SW),"rebuild rail");
  Check(AIRail.BuildRailDepot(Tile(10,29),Tile(11,29)),"depot");
  Check(AIRail.BuildSignal(Tile(30,29),Tile(29,29),AIRail.SIGNALTYPE_NORMAL_TWOWAY),"signal");
  Check(AITile.GetCargoProduction(Tile(11,29),coal,3,1,4)>0,"coal in catchment");
  Check(AITile.GetCargoAcceptance(Tile(42,29),coal,3,1,4)>=8,"coal accepted");
  local engine=-1, wagon=-1;
  foreach (id,v in AIEngineList(AIVehicle.VT_RAIL)) {
   if (AIEngine.IsWagon(id) && AIEngine.GetCargoType(id)==coal) wagon=id;
   if (!AIEngine.IsWagon(id) && AIEngine.CanRunOnRail(id,0) && engine<0) engine=id;
  }
  Check(engine>=0 && wagon>=0,"vehicle identities");
  local train=AIVehicle.BuildVehicle(Tile(10,29),engine);
  Check(AIVehicle.IsValidVehicle(train),"locomotive");
  for (local i=0;i<3;i++) {
   local w=AIVehicle.BuildVehicle(Tile(10,29),wagon);
   Check(AIVehicle.IsValidVehicle(w),"wagon");
   Check(AIVehicle.MoveWagon(w,0,train,0),"couple wagon");
  }
  Check(AIOrder.AppendOrder(train,Tile(11,29),AIOrder.OF_FULL_LOAD_ANY),"load order");
  Check(AIOrder.AppendOrder(train,Tile(42,29),AIOrder.OF_NONE),"delivery order");
  Check(AIVehicle.StartStopVehicle(train),"start train");
  print("PHASE4 ROUTE_READY train=" + train + " coal=" + coal);
  train_id=train;
  coal_id=coal;

  Monitor();
 }
}
