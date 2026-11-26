using System;using System.IO;using System.Linq;using System.Reflection;using System.Collections.Generic;using System.Collections.Concurrent;using System.Runtime.Serialization;using System.IO.Compression;using System.Xml.Linq;
using BhModule.Community.Pathing.State;using BhModule.Community.Pathing.Utility;using BhModule.Community.Pathing.Behavior;using BhModule.Community.Pathing.Entity;using BhModule.Community.Pathing.Entity.Effects;using Blish_HUD.Settings;using Gw2Sharp.WebApi.V2.Models;using TmfLib.Pathable;using TmfLib.Prototype;
namespace BhModule.Community.Pathing {
class StubState:IPackState {
public PathingModule Module => default;
public ModuleSettings UserConfiguration { get; set; }
public int CurrentMapId => default;
public PathingCategory RootCategory { get; set; }
public MarkerEffect SharedMarkerEffect => default;
public TrailEffect SharedTrailEffect => default;
public BehaviorStates BehaviorStates => default;
public AchievementStates AchievementStates { get; set; }
public RaidStates RaidStates => default;
public CategoryStates CategoryStates => default;
public MapStates MapStates => default;
public UserResourceStates UserResourceStates => default;
public UiStates UiStates => default;
public CachedMumbleStates CachedMumbleStates => default;
public KvStates KvStates => default;
public SafeList<IPathingEntity> Entities => default;
}
class IntegrationTests {
 static string dir;static int checks;static string snapshot;
 static void Assert(string name,bool test){if(!test)throw new Exception("FAIL "+name);checks++;}
 static Assembly Resolve(object sender,ResolveEventArgs e){var n=new AssemblyName(e.Name).Name;var p=n=="Pathing"?Path.Combine(dir,"Pathing.dll"):Directory.GetFiles(Path.Combine(dir,"references")).FirstOrDefault(f=>Path.GetFileNameWithoutExtension(f).Equals(n,StringComparison.OrdinalIgnoreCase));return p==null?null:Assembly.LoadFrom(p);}
 static int Main(string[] args){dir=Path.GetFullPath(args[0]);if(args.Length>1)snapshot=Console.In.ReadToEnd();AppDomain.CurrentDomain.AssemblyResolve+=Resolve;try{return Run();}catch(Exception e){Console.Error.WriteLine(e);return 1;}}
 static void Set(object instance,string field,object value){instance.GetType().GetField(field,BindingFlags.Instance|BindingFlags.NonPublic).SetValue(instance,value);}
 static StubState State(){
  var s=new StubState{RootCategory=new PathingCategory(true),AchievementStates=new AchievementStates(null)};
  s.UserConfiguration=(ModuleSettings)FormatterServices.GetUninitializedObject(typeof(ModuleSettings));
  Set(s.UserConfiguration,"<PackOrganizeCompletedAchievements>k__BackingField",(SettingEntry<bool>)Activator.CreateInstance(typeof(SettingEntry<bool>), BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic, null, new object[]{true}, null));
  Set(s.AchievementStates,"_completionDataAvailable",true);
  return s;
 }
 static void Done(StubState state,int id,bool done=true,int? repeats=null){
  var dict=(ConcurrentDictionary<int,AchievementStatus>)typeof(AchievementStates).GetField("_achievementStates",BindingFlags.Instance|BindingFlags.NonPublic).GetValue(state.AchievementStates);
  dict[id]=new AchievementStatus(new AccountAchievement{Id=id,Done=done,Repeated=repeats});
 }
 static PathingCategory Cat(PathingCategory root,string path,params string[] pairs){
  var c=root.GetOrAddCategoryFromNamespace(path);var attrs=new AttributeCollection();
  for(int i=0;i<pairs.Length;i+=2)attrs.AddOrUpdateAttribute(pairs[i],pairs[i+1]);
  c.SetAttributes(attrs);return c;
 }
 static int Run(){
  Assert("metadata embedded",CompletionUtil.Known.Count>8000);
  var state=State();
  Cat(state.RootCategory,"test","completion-track","true","displayname","Test");
  var a=Cat(state.RootCategory,"test.one","achievementid","156","displayname","Finished");
  Done(state,156);
  Assert("actual TmfLib attributes and real state",CompletionUtil.IsCompleted(a,state));
  Set(state.AchievementStates,"_completionDataAvailable",false);Assert("API unavailable",!CompletionUtil.IsCompleted(a,state));Set(state.AchievementStates,"_completionDataAvailable",true);
  var b=Cat(state.RootCategory,"test.two","achievementid","155");Done(state,155,false);Assert("in progress",!CompletionUtil.IsCompleted(b,state));
  var repeat=Cat(state.RootCategory,"test.lantern","achievementid","6239");Done(state,6239,true);Assert("lantern flag despite done",!CompletionUtil.IsCompleted(repeat,state));
  var unknown=Cat(state.RootCategory,"test.unknown","achievementid","999999");Done(state,999999);Assert("unknown ID stays available",!CompletionUtil.IsCompleted(unknown,state));
  var bit=Cat(state.RootCategory,"test.bit","achievementid","156","achievementbit","0");Assert("partial objective not full achievement",!CompletionUtil.IsCompleted(bit,state));
  var group=Cat(state.RootCategory,"test.group","completion-achievements","155,156");Assert("partly completed group",!CompletionUtil.IsCompleted(group,state));Done(state,155);Assert("fully finished group",CompletionUtil.IsCompleted(group,state));
  var invalid=Cat(state.RootCategory,"test.invalid","completion-achievements","156,invalid");Assert("invalid group stays available",!CompletionUtil.IsCompleted(invalid,state));
  var parentBit=Cat(state.RootCategory,"test.parentbit","achievementid","156");
  Cat(state.RootCategory,"test.parentbit.lantern","achievementid","6239","achievementbit","0");
  Assert("repeatable descendant bit protects parent",!CompletionUtil.IsCompleted(parentBit,state));
  var parent=Cat(state.RootCategory,"test.parent","achievementid","156");Cat(state.RootCategory,"test.parent.repeat","achievementid","6239");Assert("repeatable child protects parent",!CompletionUtil.IsCompleted(parent,state));
  Cat(state.RootCategory,"test.farm","completion-keepavailable","true");var farm=Cat(state.RootCategory,"test.farm.route","achievementid","156");Assert("farming remains available",!CompletionUtil.IsCompleted(farm,state));
  Set(state.UserConfiguration,"<PackOrganizeCompletedAchievements>k__BackingField",Activator.CreateInstance(typeof(SettingEntry<bool>), BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic, null, new object[]{false}, null));Assert("setting off",!CompletionUtil.IsCompleted(a,state));Set(state.UserConfiguration,"<PackOrganizeCompletedAchievements>k__BackingField",Activator.CreateInstance(typeof(SettingEntry<bool>), BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic, null, new object[]{true}, null));
  var repeated=Cat(state.RootCategory,"test.repeated","achievementid","156");Done(state,156,true,1);Assert("account repeated field",!CompletionUtil.IsCompleted(repeated,state));Done(state,156);
  Console.WriteLine("PASS integration: "+checks+" assertions using compiled module, real TmfLib and real AchievementStates");
  foreach(var file in Directory.GetFiles(Path.Combine(dir,"A-installer/markers"),"*.taco")){
   var pack=State();
   using(var z=ZipFile.OpenRead(file))foreach(var e in z.Entries.Where(e=>e.FullName.EndsWith(".xml",StringComparison.OrdinalIgnoreCase))){
    using(var stream=e.Open()){
     var doc=XDocument.Load(stream);
     foreach(var node in doc.Descendants().Where(n=>n.Name.LocalName.Equals("MarkerCategory",StringComparison.OrdinalIgnoreCase))){
      var names=node.AncestorsAndSelf().Where(n=>n.Name.LocalName.Equals("MarkerCategory",StringComparison.OrdinalIgnoreCase)).Reverse().Select(x=>(string)x.Attribute("name")).Where(x=>!string.IsNullOrEmpty(x));
      var path=string.Join(".",names);var c=pack.RootCategory.GetOrAddCategoryFromNamespace(path);
      var collected = new AttributeCollection(c.ExplicitAttributes);
      foreach(var attr in node.Attributes())collected.AddOrUpdateAttribute(attr.Name.LocalName,attr.Value);
      // Apply recognized category attributes as the normal pack reader does.
      c.SetAttributes(collected);
     }
    }
   }
   if(snapshot==null) foreach(var id in CompletionUtil.Known)Done(pack,id);
   else foreach(var line in snapshot.Split(new[]{'\n'},StringSplitOptions.RemoveEmptyEntries)) {
    var values=line.Trim().Split('\t');Done(pack,int.Parse(values[0]),values[1]=="1",values[2]=="-"?(int?)null:int.Parse(values[2]));
   }
   var categories=CategoryUtil.FlattenCategories(pack.RootCategory).ToList();Assert("pack categories actually read "+file,categories.Count>5000);int classified=0;int protectedRepeats=0;
   foreach(var cat in categories){
    bool complete=CompletionUtil.IsCompleted(cat,pack);if(complete)classified++;
    if(cat.ExplicitAttributes.TryGetAttribute("achievementid",out var attr)&&int.TryParse(attr.GetValueAsString(),out int id)&&CompletionUtil.Repeatable.Contains(id)){
     Assert("pack repeatable "+cat.Namespace,!complete);protectedRepeats++;
    }
   }
   var actualPack=TmfLib.Pack.FromArchivedMarkerPack(file);
   var loaded=(SharedPackCollection)Activator.CreateInstance(typeof(SharedPackCollection), BindingFlags.Instance|BindingFlags.NonPublic, null, new object[]{null,null},null);
   var readerSettings=new TmfLib.Reader.PackReaderSettings();readerSettings.VenderPrefixes.Add("bh-");
   actualPack.LoadMapAsync(15,loaded,readerSettings).GetAwaiter().GetResult();
   var realCategories=CategoryUtil.FlattenCategories(loaded.Categories).ToList();
   Assert("actual pack reader categories "+file,realCategories.Count>5000);
   Assert("actual pack reader retains tracking attributes "+file,realCategories.Any(c=>CompletionUtil.Enabled(c)));
   Assert("actual pack reader classification "+file,realCategories.Any(c=>CompletionUtil.IsCompleted(c,pack)));
   Console.WriteLine("TmfLib native reader: "+realCategories.Count+" categories loaded; custom attributes recognized");
   Console.WriteLine(Path.GetFileName(file)+": "+categories.Count+" categories parsed; "+classified+(snapshot==null?" eligible when all nonrepeatables done; ":" finished categories in live account snapshot; ")+protectedRepeats+" repeatable category bindings protected");
  }
  var tehFile=Path.Combine(dir,"../Forge de Tyrie/Forge-Packs/Tehs-Trails-FR-Classement-des-succes.taco");
  var teh=TmfLib.Pack.FromArchivedMarkerPack(tehFile);
  var tehLoaded=(SharedPackCollection)Activator.CreateInstance(typeof(SharedPackCollection), BindingFlags.Instance|BindingFlags.NonPublic, null, new object[]{null,null},null);
  var tehSettings=new TmfLib.Reader.PackReaderSettings();tehSettings.VenderPrefixes.Add("bh-");
  teh.LoadMapAsync(1442,tehLoaded,tehSettings).GetAwaiter().GetResult();
  var tehCategories=CategoryUtil.FlattenCategories(tehLoaded.Categories).ToDictionary(c=>c.Namespace);
  var exploration=tehCategories["tt.eod.succes_exploration.succes_6077"];
  var lanterns=tehCategories["tt.eodl.lantern"];
  Assert("Teh's Trails category visible to native reader",exploration.LoadedFromPack);
  var tehState=State();Done(tehState,6077,false);
  Assert("Teh's Trails exploration in progress remains in section",!CompletionUtil.IsCompleted(exploration,tehState));
  Done(tehState,6077);Done(tehState,6239);
  Assert("Teh's Trails confirmed exploration moves to completed",CompletionUtil.IsCompleted(exploration,tehState));
  Assert("Teh's Trails repeatable lanterns stay available",!CompletionUtil.IsCompleted(lanterns,tehState));
  Assert("Teh's Trails exploration routes stay available",!CompletionUtil.IsCompleted(tehCategories["tt.eod"],tehState));
  Console.WriteLine("PASS full pack integration; assertions total "+checks);return 0;
 }
}
}
