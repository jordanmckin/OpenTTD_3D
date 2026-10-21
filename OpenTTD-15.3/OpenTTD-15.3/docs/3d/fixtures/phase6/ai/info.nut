/* GPL-2.0-only */
class Coverage3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Coverage3DFixture"; }
 function GetShortName() { return "C3DF"; }
 function GetDescription() { return "Phase 6 air and water coverage via original commands."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-16"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Coverage3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Coverage3DInfo());
