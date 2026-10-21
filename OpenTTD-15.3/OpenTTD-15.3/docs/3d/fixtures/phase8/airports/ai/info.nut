/* OpenTTD Phase 8.6 fixture, GPL-2.0-only. */
class Airports3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Airports3DFixture"; }
 function GetShortName() { return "A3DF"; }
 function GetDescription() { return "Builds every original airport type through ordinary commands for airport review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-17"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Airports3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Airports3DInfo());
