/* Trailer showcase; ordinary public game commands only. GPL-2.0-only. */
import("pathfinder.road", "TrailerRoadPathfinder", 4);
class TrailerCityBuilder extends AIController {
 built=false; fleet=null; roadjobs=null; repairs=0;
 function Save(){return {built=built,fleet=fleet,roadjobs=roadjobs,repairs=repairs};}
 function Load(version,data){built=data.built;fleet=data.fleet;roadjobs=("roadjobs" in data)?data.roadjobs:[];repairs=("repairs" in data)?data.repairs:0;}
 function T(x,y){return AIMap.GetTileIndex(x,y);}
 function XY(t){return AIMap.GetTileX(t)+","+AIMap.GetTileY(t);}
 function Check(ok,label){if(!ok){print("TRAILER FAIL "+label+" "+AIError.GetLastErrorString());throw label;}}
 function NameStation(t,name){Check(AIStation.SetName(AIStation.GetStationID(t),name),"name "+name);}
 function Cargo(label){foreach(c,v in AICargoList())if(AICargo.GetCargoLabel(c)==label)return c;throw "Missing cargo "+label;}
 function Industry(type,x,y,label){Check(AIIndustryType.BuildIndustry(type,T(x,y)),"industry "+label);print("TRAILER INDUSTRY "+label+" xy="+x+","+y);}
 function Level(x0,y0,x1,y1){print("TRAILER LEVEL "+x0+","+y0+" result="+AITile.LevelTiles(T(x1,y1),T(x0,y0))+" "+AIError.GetLastErrorString());}
 function Goodwill(){
  foreach(town,val in AITownList())if(AITown.GetDistanceManhattanToTile(town,T(900,150))<75){
   local c=AITown.GetLocation(town);
   print("TRAILER TREES town="+AITown.GetName(town)+" planted="+AITile.PlantTreeRectangle(c-T(10,10),20,20));
  }
 }
 function Loop(y,label,cargo,loco,tunnel){
  Goodwill();
  local x0=879,x1=915,y1=y+4,a=T(883,y),b=T(907,y),depot=T(878,y);
  Check(AIRail.BuildRailStation(a,AIRail.RAILTRACK_NE_SW,1,4,AIStation.STATION_NEW),label+" source platform");
  Check(AIRail.BuildRailStation(b,AIRail.RAILTRACK_NE_SW,1,4,AIStation.STATION_NEW),label+" destination platform");
  NameStation(a,label+" Loading");NameStation(b,label+" Works");
  local path=[];
  for(local x=x0;x<=x1;x++)path.append(T(x,y));
  for(local yy=y+1;yy<=y1;yy++)path.append(T(x1,yy));
  for(local x=x1-1;x>=x0;x--)path.append(T(x,y1));
  for(local yy=y1-1;yy>y;yy--)path.append(T(x0,yy));
  if(tunnel){
   for(local x=896;x<=900;x++)for(local yy=y-2;yy<=y+2;yy++)Check(AITile.RaiseTile(T(x,yy),AITile.SLOPE_N),"tunnel hill");
   Check(AITunnel.BuildTunnel(AIVehicle.VT_RAIL,T(895,y)),"timber tunnel");
   Check(AITunnel.GetOtherTunnelEnd(T(895,y))==T(900,y),"timber tunnel exit");
  }
  for(local i=0;i<path.len();i++){
   local t=path[i],x=AIMap.GetTileX(t),yy=AIMap.GetTileY(t);
   if(AIRail.IsRailStationTile(t))continue;
   if(tunnel&&yy==y&&x>=895&&x<=900)continue;
   Check(AIRail.BuildRail(path[(i+path.len()-1)%path.len()],t,path[(i+1)%path.len()]),label+" track "+XY(t));
  }
  Check(AIRail.BuildRailDepot(depot,T(879,y)),label+" depot");
  Check(AIRail.BuildRailTrack(T(879,y),AIRail.RAILTRACK_NE_SW),label+" depot lead");
  for(local i=1;i<path.len();i++){
   local t=path[i],x=AIMap.GetTileX(t),yy=AIMap.GetTileY(t);
   if(AIRail.IsRailStationTile(t)||AITunnel.IsTunnelTile(t)||(tunnel&&yy==y&&x>=895&&x<=900))continue;
   if((yy==y||yy==y1)&&x>x0&&x<x1&&(x-x0)%6==1)Check(AIRail.BuildSignal(t,path[(i+path.len()-1)%path.len()],AIRail.SIGNALTYPE_NORMAL),label+" signal "+XY(t));
  }
  Check(AITile.GetCargoProduction(a,cargo,4,1,4)>0,label+" source catchment");
  Check(AITile.GetCargoAcceptance(b,cargo,4,1,4)>=8,label+" destination catchment");
  local wagon=-1;
  foreach(e,v in AIEngineList(AIVehicle.VT_RAIL))if(AIEngine.IsBuildable(e)&&AIEngine.IsWagon(e)&&AIEngine.GetCargoType(e)==cargo){wagon=e;break;}
  Check(wagon>=0,"wagon for "+label);Check(AIEngine.IsBuildable(loco),"locomotive for "+label);
  for(local n=0;n<3;n++){
   local train=AIVehicle.BuildVehicle(depot,loco);Check(AIVehicle.IsValidVehicle(train),label+" locomotive");
   for(local k=0;k<4;k++){local w=AIVehicle.BuildVehicle(depot,wagon);Check(AIVehicle.IsValidVehicle(w),label+" wagon");Check(AIVehicle.MoveWagon(w,0,train,0),"couple "+label);}
   Check(AIVehicle.SetName(train,label+" Freight "+(n+1)),"train name");
   Check(AIOrder.AppendOrder(train,a,AIOrder.OF_NONE),"train load order");Check(AIOrder.AppendOrder(train,b,AIOrder.OF_NONE),"train unload order");
   Check(AIVehicle.StartStopVehicle(train),"start "+label);fleet.append(train);this.Sleep(40);
  }
  print("TRAILER ROUTE "+label+" a="+XY(a)+" b="+XY(b)+" cargo="+cargo);
 }
 function BridgeRoad(a,b,label){local ok=false;foreach(id,v in AIBridgeList_Length(AIMap.DistanceManhattan(a,b)+1)){
  local result=AIBridge.BuildBridge(AIVehicle.VT_ROAD,id,a,b);
  print("TRAILER BRIDGE_TRY id="+id+" result="+result+" exists="+AIBridge.IsBridgeTile(a)+" error="+AIError.GetLastError()+" "+AIError.GetLastErrorString());
  if(result || (AIBridge.IsBridgeTile(a)&&AIBridge.GetOtherBridgeEnd(a)==b)){ok=true;break;}
 }
Check(ok,label);}
 function Road(a,b,label){Check(AIRoad.AreRoadTilesConnected(a,b)||AIRoad.BuildRoad(a,b),label);}
 function TruckStop(x,y,label,cargo,source){
  local t=T(x,y);Check(AIRoad.BuildDriveThroughRoadStation(t,T(x+1,y),AIRoad.ROADVEHTYPE_TRUCK,AIStation.STATION_NEW),label+" stop");NameStation(t,label);
  print("TRAILER STOP "+label+" production="+AITile.GetCargoProduction(t,cargo,1,1,3)+" acceptance="+AITile.GetCargoAcceptance(t,cargo,1,1,3));
  Check(source?AITile.GetCargoProduction(t,cargo,1,1,3)>0:AITile.GetCargoAcceptance(t,cargo,1,1,3)>=8,label+" catchment");return t;
 }
 function RoadEngine(cargo){local best=-1,speed=0;foreach(e,v in AIEngineList(AIVehicle.VT_ROAD))if(AIEngine.IsBuildable(e)&&AIEngine.GetCargoType(e)==cargo&&AIEngine.GetMaxSpeed(e)>speed){best=e;speed=AIEngine.GetMaxSpeed(e);}
Check(best>=0,"road engine cargo "+cargo);return best;}
 function RoadFleet(depot,a,b,cargo,count,label){
  local e=RoadEngine(cargo);
  for(local n=0;n<count;n++){
   local v=AIVehicle.BuildVehicle(depot,e);Check(AIVehicle.IsValidVehicle(v),label+" vehicle");Check(AIVehicle.SetName(v,label+" "+(n+1)),"road vehicle name");
   Check(AIOrder.AppendOrder(v,a,AIOrder.OF_NONE),label+" pickup");Check(AIOrder.AppendOrder(v,b,AIOrder.OF_NONE),label+" delivery");
   Check(AIVehicle.StartStopVehicle(v),label+" start");fleet.append(v);roadjobs.append({vehicle=v,depot=depot,a=a,b=b,cargo=cargo,label=label});this.Sleep(20);
  }
 }
 function LinkRoad(a,b,label){
  local pf=TrailerRoadPathfinder();pf.cost.max_bridge_length=20;pf.cost.max_tunnel_length=30;
  pf.InitializePath([a],[b]);local path=false;
  for(local n=0;n<100&&path==false;n++){path=pf.FindPath(1500);if(path==false)this.Sleep(1);}
  Check(path!=null&&path!=false,label+" path");
  while(path.GetParent()!=null){
   local a=path.GetTile(),b=path.GetParent().GetTile();
   if(AIMap.DistanceManhattan(a,b)==1)Road(a,b,label+" road "+XY(a));
   else if((AIBridge.IsBridgeTile(a)&&AIBridge.GetOtherBridgeEnd(a)==b)||(AITunnel.IsTunnelTile(a)&&AITunnel.GetOtherTunnelEnd(a)==b)){}
   else if(AITunnel.GetOtherTunnelEnd(a)==b)Check(AITunnel.BuildTunnel(AIVehicle.VT_ROAD,a),label+" tunnel");
   else BridgeRoad(a,b,label+" bridge");
   path=path.GetParent();
  }
 }
 function TownStop(town,used,cargo,goods){
  local centre=AITown.GetLocation(town),tiles=AITileList();tiles.AddRectangle(centre-T(12,12),centre+T(12,12));tiles.Valuate(AIMap.DistanceManhattan,centre);tiles.Sort(AIList.SORT_BY_VALUE,true);
  foreach(t,v in tiles){
   if(!AIRoad.IsRoadTile(t)||AIRoad.IsRoadStationTile(t)||AIBridge.IsBridgeTile(t)||AITunnel.IsTunnelTile(t)||AITile.GetSlope(t)!=AITile.SLOPE_FLAT)continue;
   local far=true;foreach(u in used)if(AIMap.DistanceManhattan(t,u)<7)far=false;if(!far)continue;
   if(goods&&AITile.GetCargoAcceptance(t,cargo,1,1,3)<8)continue;
   foreach(o in [1,AIMap.GetMapSizeX()]){
    if(!AIRoad.AreRoadTilesConnected(t,t+o)||!AIRoad.AreRoadTilesConnected(t,t-o))continue;
    if(AIRoad.BuildDriveThroughRoadStation(t,t+o,goods?AIRoad.ROADVEHTYPE_TRUCK:AIRoad.ROADVEHTYPE_BUS,AIStation.STATION_NEW))return t;
   }
  }
  throw "No town stop "+AITown.GetName(town);
 }
 function TownDepot(town){
  local centre=AITown.GetLocation(town),tiles=AITileList();tiles.AddRectangle(centre-T(16,16),centre+T(16,16));tiles.Valuate(AIMap.DistanceManhattan,centre);tiles.Sort(AIList.SORT_BY_VALUE,true);
  foreach(t,v in tiles){
   if(!AITile.IsBuildable(t)||AITile.GetSlope(t)!=AITile.SLOPE_FLAT)continue;
   foreach(o in [1,-1,AIMap.GetMapSizeX(),-AIMap.GetMapSizeX()]){
    if(!AIRoad.IsRoadTile(t+o)||AIRoad.IsRoadStationTile(t+o))continue;
    if(AIRoad.BuildRoadDepot(t,t+o)){Road(t,t+o,"town depot connection");return t;}
   }
  }
  throw "No depot "+AITown.GetName(town);
 }
 function TownBuses(town,label){
  local p=Cargo("PASS"),a=TownStop(town,[],p,false),b=TownStop(town,[a],p,false),depot=TownDepot(town);
  LinkRoad(a,b,label+" bus link");NameStation(a,label+" Central");NameStation(b,label+" Riverside");RoadFleet(depot,a,b,p,8,label+" Bus");
  print("TRAILER BUS_ROUTE "+label+" a="+XY(a)+" b="+XY(b));
 }
 function Build(){
  fleet=[];roadjobs=[];AIRail.SetCurrentRailType(0);AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);AIController.SetCommandDelay(1);
  Check(AICompany.SetName("Trailer Transport"),"company name");AICompany.SetPrimaryLiveryColour(AICompany.LS_DEFAULT,AICompany.COLOUR_DARK_BLUE);
  Check(AITile.LevelTiles(T(915,152),T(878,126)),"district north terrace");Check(AITile.LevelTiles(T(878,126),T(917,167)),"district terrace");Level(929,145,936,153);
  Industry(18,882,128,"Iron Ore Mine");Industry(8,907,128,"Steel Mill");Industry(0,882,141,"Coal Mine");Industry(1,907,143,"Power Station");Industry(6,931,147,"Factory");Industry(3,882,154,"Forest");Industry(2,907,156,"Sawmill");
  Loop(134,"Iron",Cargo("IORE"),15,false);Loop(147,"Coal",Cargo("COAL"),13,false);Loop(160,"Timber",Cargo("WOOD"),10,true);
  foreach(p in [T(898,130),T(898,142)])print("TRAILER BRIDGE_SITE "+XY(p)+" slope="+AITile.GetSlope(p)+" height="+AITile.GetMinHeight(p));
  foreach(yy in [130,142])for(local x=898;x<=899;x++)for(local y=yy;y<=yy+1;y++){while(AITile.GetCornerHeight(T(x,y),AITile.CORNER_N)<9)Check(AITile.RaiseTile(T(x,y),AITile.SLOPE_N),"bridge pad");while(AITile.GetCornerHeight(T(x,y),AITile.CORNER_N)>9)Check(AITile.LowerTile(T(x,y),AITile.SLOPE_N),"bridge pad");}
  foreach(p in [T(898,130),T(898,142)])print("TRAILER BRIDGE_READY "+XY(p)+" slope="+AITile.GetSlope(p)+" height="+AITile.GetMinHeight(p));BridgeRoad(T(898,130),T(898,142),"freight avenue flyover");
  for(local y=127;y<=166;y++){if(y>=130&&y<142)continue;local rx=y>=142?899:898;Road(T(rx,y),T(rx,y+1),"freight avenue "+y);}
  local all=AITile.SLOPE_N|AITile.SLOPE_E|AITile.SLOPE_S|AITile.SLOPE_W;
  Road(T(898,129),T(898,130),"flyover north approach");Road(T(898,142),T(898,143),"flyover south approach");
  foreach(y in [127,140,153]){Road(T(881,y),T(895,y),"west loading road");Road(T(899,y),T(913,y),"east loading road");Road(T(895,y),T(899,y),"loading road junction");}
  Road(T(894,140),T(894,143),"flyover service road");Road(T(894,143),T(898,143),"flyover service link");Road(T(881,140),T(881,153),"freight avenue link");
  local depot=T(898,166);Check(AIRoad.BuildRoadDepot(depot,T(899,166)),"freight road depot");Road(depot,T(899,166),"freight road depot connection");
  Road(T(913,140),T(913,142),"power road approach");Road(T(909,142),T(913,142),"power road frontage");Road(T(913,153),T(913,155),"sawmill road approach");Road(T(909,155),T(913,155),"sawmill road frontage");
  local coal=Cargo("COAL"),wood=Cargo("WOOD"),iron=Cargo("IORE"),steel=Cargo("STEL"),goods=Cargo("GOOD");
  local ca=TruckStop(885,140,"Coal Loading Road",coal,true),cb=TruckStop(909,142,"Power Delivery Road",coal,false);
  local wa=TruckStop(885,153,"Timber Loading Road",wood,true),wb=TruckStop(909,155,"Sawmill Delivery Road",wood,false);
  local ia=TruckStop(885,127,"Ore Loading Road",iron,true),ib=TruckStop(909,127,"Steel Mill Road",iron,false);
  LinkRoad(T(913,153),T(934,146),"factory road");Road(T(934,146),T(935,146),"factory road frontage");local fa=TruckStop(934,146,"Factory Logistics",steel,false);
  RoadFleet(depot,ca,cb,coal,4,"Coal Haulage");RoadFleet(depot,wa,wb,wood,4,"Timber Haulage");RoadFleet(depot,ia,ib,iron,3,"Ore Haulage");RoadFleet(depot,ib,fa,steel,3,"Steel Haulage");
  Road(T(934,146),T(935,146),"dispatch north link");Road(T(935,146),T(935,151),"dispatch access");Road(T(934,151),T(935,151),"dispatch frontage");
  local ga=TruckStop(934,151,"Factory Dispatch",goods,true);
  local city=TownStop(175,[],goods,true);NameStation(city,"Lewisworth Goods Exchange");LinkRoad(T(913,153),city,"Lewisworth freight connection");RoadFleet(depot,ga,city,goods,4,"City Goods");
  TownBuses(175,"Lewisworth");TownBuses(215,"Whitdon");built=true;print("TRAILER BUILD_DONE vehicles="+fleet.len());
 }
 function Monitor(){
  for(;;){
   AIRoad.SetCurrentRoadType(AIRoad.ROADTYPE_ROAD);
   foreach(job in roadjobs)if(!AIVehicle.IsValidVehicle(job.vehicle)||AIVehicle.GetState(job.vehicle)==AIVehicle.VS_CRASHED){
    local v=AIVehicle.BuildVehicle(job.depot,RoadEngine(job.cargo));
    if(AIVehicle.IsValidVehicle(v)){
     AIOrder.AppendOrder(v,job.a,AIOrder.OF_NONE);AIOrder.AppendOrder(v,job.b,AIOrder.OF_NONE);repairs++;
     AIVehicle.SetName(v,job.label+" R"+repairs);AIVehicle.StartStopVehicle(v);
     for(local n=0;n<fleet.len();n++)if(fleet[n]==job.vehicle)fleet[n]=v;
     job.vehicle=v;print("TRAILER REPLACED vehicle="+v);
    }
   }
   local moving=0,loaded=0,profit=0;
   foreach(v in fleet)if(AIVehicle.IsValidVehicle(v)){
    if(AIVehicle.GetCurrentSpeed(v)>0)moving++;local load=0;foreach(c,val in AICargoList())load+=AIVehicle.GetCargoLoad(v,c);if(load>0)loaded++;
    profit+=AIVehicle.GetProfitThisYear(v)+AIVehicle.GetProfitLastYear(v);
    print("TRAILER VEHICLE id="+v+" name="+AIVehicle.GetName(v)+" xy="+XY(AIVehicle.GetLocation(v))+" speed="+AIVehicle.GetCurrentSpeed(v)+" load="+load+" profit="+(AIVehicle.GetProfitThisYear(v)+AIVehicle.GetProfitLastYear(v)));
   }
   print("TRAILER STATUS fleet="+fleet.len()+" moving="+moving+" loaded="+loaded+" profit="+profit);this.Sleep(740);
  }
 }
 function Start(){if(!built)Build();else print("TRAILER RELOADED vehicles="+fleet.len());Monitor();}
}
