/* GPL-2.0-only. Diagonal join regression through ordinary rail commands. */
class Diagonal3DFixture extends AIController {
 function Build(x,y,track) {
  if (!AIRail.BuildRailTrack(AIMap.GetTileIndex(x,y),track)) throw "DIAGONAL FAILED " + x + "," + y + " " + AIError.GetLastErrorString();
 }
 function Start() {
  AICompany.SetLoanAmount(AICompany.GetMaxLoanAmount());
  AIRail.SetCurrentRailType(0);
  for (local i=0;i<6;i++) {
   Build(24+i,36-i,AIRail.RAILTRACK_NW_NE);
   Build(24+i,35-i,AIRail.RAILTRACK_SW_SE);
   Build(24+i,40+i,AIRail.RAILTRACK_NW_SW);
   Build(25+i,40+i,AIRail.RAILTRACK_NE_SE);
  }
  print("DIAGONAL READY pieces=24");
  for (;;) this.Sleep(100);
 }
}
