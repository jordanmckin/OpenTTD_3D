/* OpenTTD Phase 3 fixture, GPL-2.0-only. */
class Railway3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Railway3DFixture"; }
 function GetShortName() { return "R3DF"; }
 function GetDescription() { return "Builds an isolated coal railway through ordinary game commands for renderer validation."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-16"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Railway3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Railway3DInfo());
