class TrailerCityBuilder extends AIController {
 function Region(label,x0,y0,w,h) {
  print("TRAILER REGION " + label + " " + x0 + " " + y0 + " " + w + " " + h);
  for (local y=y0;y<y0+h;y++) {
   local row="", heights="";
   for (local x=x0;x<x0+w;x++) {
    local t=AIMap.GetTileIndex(x,y), c=".";
    if (AITile.IsWaterTile(t)) c="w";
    else if (AITile.IsHouseTile(t)) c="h";
    else if (AIIndustry.IsValidIndustry(AIIndustry.GetIndustryID(t))) c="i";
    else if (AIRail.IsRailTile(t) || AIRail.IsRailDepotTile(t)) c="t";
    else if (AIRoad.IsRoadTile(t) || AIRoad.IsRoadDepotTile(t) || AIRoad.IsRoadStationTile(t)) c="r";
    else if (!AITile.IsBuildable(t)) c="o";
    row+=c; heights+=AITile.GetCornerHeight(t,AITile.CORNER_N)+",";
   }
   print("TRAILER ROW " + label + " " + y + " " + row + " " + heights);
  }
 }
 function XY(t) { return AIMap.GetTileX(t) + "," + AIMap.GetTileY(t); }
 function Start() {
  AICompany.SetName("Trailer Transport");
  print("TRAILER MAP " + AIMap.GetMapSizeX() + "x" + AIMap.GetMapSizeY() + " company=" + AICompany.ResolveCompanyID(AICompany.COMPANY_SELF));
  for (local id=0;id<15;id++) if (AICompany.ResolveCompanyID(id)!=AICompany.COMPANY_INVALID) print("TRAILER COMPANY " + id + " " + AICompany.GetName(id));
  foreach (id,v in AITownList()) print("TRAILER TOWN " + id + " " + AITown.GetName(id) + " xy=" + XY(AITown.GetLocation(id)) + " pop=" + AITown.GetPopulation(id));
  foreach (id,v in AIIndustryList()) print("TRAILER INDUSTRY " + id + " " + AIIndustry.GetName(id) + " xy=" + XY(AIIndustry.GetLocation(id)) + " type=" + AIIndustry.GetIndustryType(id));
  foreach (id,v in AIIndustryTypeList()) print("TRAILER TYPE " + id + " " + AIIndustryType.GetName(id) + " build=" + AIIndustryType.CanBuildIndustry(id));
  print("TRAILER SURVEY_DONE");
  foreach (e,v in AIEngineList(AIVehicle.VT_RAIL)) print("TRAILER ENGINE " + e + " " + AIEngine.GetName(e) + " wagon=" + AIEngine.IsWagon(e) + " cargo=" + AIEngine.GetCargoType(e) + " speed=" + AIEngine.GetMaxSpeed(e));
  foreach (e,v in AIEngineList(AIVehicle.VT_ROAD)) print("TRAILER ROADENGINE " + e + " " + AIEngine.GetName(e) + " cargo=" + AIEngine.GetCargoType(e));
  Region("Lewisworth",875,80,140,160);
  Region("Whitdon",565,20,140,130);
  for (;;) this.Sleep(1000);
 }
}
