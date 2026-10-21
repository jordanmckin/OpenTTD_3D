/* OpenTTD Phase 8.6 fixture, GPL-2.0-only. */
class Bridges3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Bridges3DFixture"; }
 function GetShortName() { return "B3DF"; }
 function GetDescription() { return "Builds every original bridge type and both tunnel kinds through ordinary commands for bridge review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-17"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Bridges3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Bridges3DInfo());
