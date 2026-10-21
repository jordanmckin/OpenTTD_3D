/* OpenTTD Phase 8.6 fixture, GPL-2.0-only. */
class Stations3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Stations3DFixture"; }
 function GetShortName() { return "S3DF"; }
 function GetDescription() { return "Builds stations, stops, depots and water infrastructure through ordinary commands for station review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-17"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Stations3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Stations3DInfo());
