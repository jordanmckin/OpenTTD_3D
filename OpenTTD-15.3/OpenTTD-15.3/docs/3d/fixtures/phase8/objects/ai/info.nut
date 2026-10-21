/* OpenTTD Phase 8.6 fixture, GPL-2.0-only. */
class Objects3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Objects3DFixture"; }
 function GetShortName() { return "O3DF"; }
 function GetDescription() { return "Builds a company HQ and a town statue through ordinary commands for map object review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-17"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Objects3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Objects3DInfo());
