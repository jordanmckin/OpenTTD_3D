class TrailerCityInfo extends AIInfo {
 function GetAuthor() { return "OpenTTD 3D contributors"; }
 function GetName() { return "TrailerCityBuilder"; }
 function GetShortName() { return "TRLR"; }
 function GetDescription() { return "Builds the transport network for the trailer showcase save through ordinary game commands."; }
 function GetVersion() { return 1; }
 function GetDate() { return "2026-10-20"; }
 function GetAPIVersion() { return "15"; }
 function CreateInstance() { return "TrailerCityBuilder"; }
 function UseAsRandomAI() { return false; }
}
RegisterAI(TrailerCityInfo());
