/* OpenTTD Phase 4 fixture, GPL-2.0-only. */
class Infrastructure3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Infrastructure3DFixture"; }
 function GetShortName() { return "I3DF"; }
 function GetDescription() { return "Builds rail and road routes, bridges, tunnels, slopes and a crossing through ordinary commands for renderer validation."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-16"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Infrastructure3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Infrastructure3DInfo());
