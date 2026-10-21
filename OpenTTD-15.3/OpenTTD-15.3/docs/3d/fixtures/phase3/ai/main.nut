/* OpenTTD Phase 3 fixture, GPL-2.0-only. No rendering callbacks or direct simulation writes. */
class Railway3DFixture extends AIController {
 train_id = null;
 coal_id = null;
 branch_done = false;
 function Save() { return {train=train_id,coal=coal_id,branch=branch_done}; }
 function Load(version,data) { this.train_id=data.train; this.coal_id=data.coal; this.branch_done=("branch" in data)?data.branch:false; }
 function Branch() {
  if (branch_done) return;
  AIRail.SetCurrentRailType(0);
  Check(AIRail.BuildRailTrack(Tile(36,29),AIRail.RAILTRACK_NW_SW),"junction");
  Check(AIRail.BuildRailTrack(Tile(36,28),AIRail.RAILTRACK_NW_SE),"branch straight");
  Check(AIRail.BuildRailTrack(Tile(36,27),AIRail.RAILTRACK_NE_SE),"branch corner");
  Check(AIRail.BuildRailTrack(Tile(35,27),AIRail.RAILTRACK_NE_SW),"branch end");
  branch_done=true;
 }
 function Monitor() {
  for (;;) {
   print("PHASE3 RUN tile=" + AIVehicle.GetLocation(train_id) + " load=" + AIVehicle.GetCargoLoad(train_id,coal_id) + " profit=" + AIVehicle.GetProfitThisYear(train_id));
   this.Sleep(250);
  }
 }
 function Tile(x,y) { return AIMap.GetTileIndex(x,y); }
 function Check(ok,label) {
  print("PHASE3 " + label + "=" + ok + " error=" + AIError.GetLastErrorString());
  if (!ok) throw "Fixture failed: " + label;
 }
 function Start() {
  if (train_id != null && AIVehicle.IsValidVehicle(train_id)) { print("PHASE3 RELOADED train=" + train_id); Branch(); Monitor(); }
  AICompany.SetName("3D Coal Railway");
  Check(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"loan");
  AIRail.SetCurrentRailType(0);
  Check(AITile.LevelTiles(Tile(8,18),Tile(50,32)),"level site");
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
   print("PHASE3 SITE x=" + x + " buildable=" + AITile.IsBuildable(tile) + " industry=" + AIIndustry.GetIndustryID(tile));
   if (!AITile.IsBuildable(tile)) Check(AITile.DemolishTile(tile),"clear route " + x);
  }
  Check(AIRail.BuildRailStation(Tile(11,29),AIRail.RAILTRACK_NE_SW,1,3,AIStation.STATION_NEW),"mine station");
  Check(AIRail.BuildRailStation(Tile(42,29),AIRail.RAILTRACK_NE_SW,1,3,AIStation.STATION_NEW),"power station platform");
  for (local x=14;x<42;x++) Check(AIRail.BuildRailTrack(Tile(x,29),AIRail.RAILTRACK_NE_SW),"track " + x);
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
  print("PHASE3 ROUTE_READY train=" + train + " coal=" + coal);
  train_id=train;
  coal_id=coal;
  Branch();
  Monitor();
 }
}
