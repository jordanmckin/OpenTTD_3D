/* OpenTTD Phase 8.6 fixture, GPL-2.0-only: a company HQ and a statue in the largest town. */
class Objects3DFixture extends AIController {
 function Start() {
  AICompany.SetName("3D Objects");
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  local towns = AITownList();
  towns.Valuate(AITown.GetPopulation);
  towns.Sort(AIList.SORT_BY_VALUE, false);
  local town = towns.Begin();
  local centre = AITown.GetLocation(town);
  print("PHASE8 FIXTURE town=" + AITown.GetName(town) + " x=" + AIMap.GetTileX(centre) + " y=" + AIMap.GetTileY(centre));
  print("PHASE8 FIXTURE statue=" + AITown.PerformTownAction(town, AITown.TOWN_ACTION_BUILD_STATUE));
  /* The HQ: the first 2x2 site found spiralling out from the town centre. */
  local built = false;
  for (local r = 3; r < 20 && !built; r++) {
   for (local dx = -r; dx <= r && !built; dx++) foreach (dy in [-r, r]) {
    local tile = AIMap.GetTileIndex(AIMap.GetTileX(centre) + dx, AIMap.GetTileY(centre) + dy);
    if (AIMap.IsValidTile(tile) && AICompany.BuildCompanyHQ(tile)) {
     print("PHASE8 FIXTURE hq x=" + AIMap.GetTileX(tile) + " y=" + AIMap.GetTileY(tile));
     built = true;
     break;
    }
   }
  }
  if (!built) print("PHASE8 FIXTURE hq failed");
  while (true) this.Sleep(1000);
 }
}
