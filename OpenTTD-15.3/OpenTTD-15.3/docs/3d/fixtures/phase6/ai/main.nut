/* GPL-2.0-only. All fixture construction uses ordinary AI commands. */
class Coverage3DFixture extends AIController {
 vehicles = null;
 function Tile(x,y) { return AIMap.GetTileIndex(x,y); }
 function Check(ok,label) { print("PHASE6 " + label + "=" + ok + " error=" + AIError.GetLastErrorString()); if (!ok) throw "PHASE6 FAILED " + label; }
 function Save() { return {vehicles=vehicles}; }
 function Load(version,data) { vehicles=data.vehicles; }
 function Monitor() {
  for (;;) {
   foreach (v in vehicles) print("PHASE6 MOVEMENT vehicle="+v+" type="+AIVehicle.GetVehicleType(v)+" tile="+AIVehicle.GetLocation(v)+" speed="+AIVehicle.GetCurrentSpeed(v));
   this.Sleep(30);
  }
 }
 function Platform(x,y,w,h) {
  while (AITile.GetCornerHeight(Tile(x,y),AITile.CORNER_N)<2) Check(AITile.RaiseTile(Tile(x,y),AITile.SLOPE_N),"raise platform anchor");
  Check(AITile.LevelTiles(Tile(x,y),Tile(x+w,y+h)),"level platform");
  for (local xx=x;xx<=x+w;xx++) for(local yy=y;yy<=y+h;yy++) {
   local t=Tile(xx,yy);
   while(AITile.GetCornerHeight(t,AITile.CORNER_N)<2) Check(AITile.RaiseTile(t,AITile.SLOPE_N),"finish platform raise");
   while(AITile.GetCornerHeight(t,AITile.CORNER_N)>2) Check(AITile.LowerTile(t,AITile.SLOPE_N),"finish platform lower");
  }
 }
 function FindSite(x0,x1) {
  for (local y=4;y<32;y++) for(local x=x0;x<x1;x++) if (AITile.IsBuildableRectangle(Tile(x-1,y-1),11,10)) return [x,y];
  throw "PHASE6 FAILED no clear airport site";
 }
 function Start() {
  if (vehicles!=null) { print("PHASE6 RELOADED"); Monitor(); }
  vehicles=[];
  Check(AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount()),"loan");
  local west=FindSite(4,22),east=FindSite(40,52);
  Platform(west[0],west[1],8,7); Platform(east[0],east[1],8,7);
  local a=Tile(west[0]+1,west[1]+1),b=Tile(east[0]+1,east[1]+1);
  for(local x=1;x<55;x+=10) for(local y=1;y<55;y+=10) AITile.PlantTreeRectangle(Tile(x,y),8,8);
  print("PHASE6 AIRPORT_SITES west="+a+" east="+b);
  Check(AIAirport.BuildAirport(a,AIAirport.AT_SMALL,AIStation.STATION_NEW),"west airport");
  Check(AIAirport.BuildAirport(b,AIAirport.AT_SMALL,AIStation.STATION_NEW),"east airport");
  local aircraft=-1;
  foreach (e,v in AIEngineList(AIVehicle.VT_AIR)) if (AIEngine.IsBuildable(e)) { aircraft=e; break; }
  Check(aircraft>=0,"aircraft available");
  local plane=AIVehicle.BuildVehicle(AIAirport.GetHangarOfAirport(a),aircraft);
  Check(AIVehicle.IsValidVehicle(plane),"build aircraft");
  Check(AIOrder.AppendOrder(plane,a,AIOrder.OF_NONE),"west air order");
  Check(AIOrder.AppendOrder(plane,b,AIOrder.OF_NONE),"east air order");
  Check(AIVehicle.StartStopVehicle(plane),"start aircraft"); vehicles.append(plane);
  Platform(10,42,24,5);
  for (local x=11;x<=33;x++) for(local y=43;y<=45;y++) Check(AIMarine.BuildCanal(Tile(x,y)),"canal");
  Check(AIMarine.BuildWaterDepot(Tile(12,44),Tile(13,44)),"ship depot");
  Check(AIMarine.BuildBuoy(Tile(18,44)),"west buoy");
  Check(AIMarine.BuildBuoy(Tile(30,44)),"east buoy");
  local ship_engine=-1;
  foreach (e,v in AIEngineList(AIVehicle.VT_WATER)) if(AIEngine.IsBuildable(e)) { ship_engine=e; break; }
  Check(ship_engine>=0,"ship available");
  local ship=AIVehicle.BuildVehicle(Tile(12,44),ship_engine);
  Check(AIVehicle.IsValidVehicle(ship),"build ship");
  Check(AIOrder.AppendOrder(ship,Tile(18,44),AIOrder.OF_NONE),"west ship order");
  Check(AIOrder.AppendOrder(ship,Tile(30,44),AIOrder.OF_NONE),"east ship order");
  Check(AIVehicle.StartStopVehicle(ship),"start ship"); vehicles.append(ship);
  print("PHASE6 READY"); Monitor();
 }
}
