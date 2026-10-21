/* OpenTTD Phase 9.5 fixture, GPL-2.0-only. */
class Air3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Air3DFixture"; }
 function GetShortName() { return "A3D9"; }
 function GetDescription() { return "Builds airports, planes and helicopters through ordinary commands for ride-along view checks."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-19"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Air3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Air3DInfo());
