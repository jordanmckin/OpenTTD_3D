/* OpenTTD Phase 8.6 fixture, GPL-2.0-only. */
class Catenary3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Catenary3DFixture"; }
 function GetShortName() { return "C3DF"; }
 function GetDescription() { return "Builds electrified track in every catenary situation through ordinary commands for catenary review."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-17"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Catenary3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Catenary3DInfo());
