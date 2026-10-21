/* GPL-2.0-only */
class Diagonal3DInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "Diagonal3DFixture"; }
 function GetShortName() { return "D3DF"; }
 function GetDescription() { return "Diagonal rail joins via original construction commands."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-16"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "Diagonal3DFixture"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(Diagonal3DInfo());
