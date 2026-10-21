/* OpenTTD Phase 7 fleet fixture, GPL-2.0-only. */
class Fleet3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Fleet3DFixture"; }
 function GetShortName() { return "F3DF"; }
 function GetDescription() { return "Builds bus services in the towns nearest the map centre and shuttle trains beside them through ordinary commands, for renderer benchmarks."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-18"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Fleet3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Fleet3DInfo());
