/* OpenTTD Phase 8.7 fixture, GPL-2.0-only. */
class Effects3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Effects3DFixture"; }
 function GetShortName() { return "E3DF"; }
 function GetDescription() { return "Builds animated industries, smoking trains, a train crash and roadworks through ordinary commands for effects review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-18"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Effects3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Effects3DInfo());
