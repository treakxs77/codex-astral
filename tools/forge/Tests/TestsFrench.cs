using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Resources;
using System.Globalization;
using BhModule.Community.Pathing;
using Humanizer;

class TestsFrench {
    static string dir;
    static int checks;
    static void Check(string name, bool ok) { if (!ok) throw new Exception("FAIL " + name); checks++; }
    static Assembly Resolve(object sender, ResolveEventArgs e) {
        string n = new AssemblyName(e.Name).Name;
        string p = n == "Pathing" ? Path.Combine(dir,"Pathing.dll") : Directory.GetFiles(Path.Combine(dir,"references")).FirstOrDefault(f => Path.GetFileNameWithoutExtension(f).Equals(n,StringComparison.OrdinalIgnoreCase));
        return p == null ? null : Assembly.LoadFrom(p);
    }
    static int Main(string[] args) {
        dir=Path.GetFullPath(args[0]); AppDomain.CurrentDomain.AssemblyResolve += Resolve;
        try { Run(args[1]); Console.WriteLine("PASS French module: " + checks + " checks"); return 0; }
        catch(Exception e) { Console.Error.WriteLine(e); return 1; }
    }
    static void Run(string packs) {
        var assembly=typeof(ModuleSettings).Assembly;
        var language=assembly.GetType("BhModule.Community.Pathing.MarkerPackRepo.PackLanguage",true);
        Func<string,string> label=f=>(string)language.GetMethod("DownloadLabel").Invoke(null,new object[]{f});
        Check("French download",label("reactif.fr.taco")=="FR");
        Check("English download",label("reactif.en.taco")=="US");
        Check("bilingual download",label("MoW.taco")=="FR/US");
        Check("no text",label("AutomaticArrows.taco")=="Sans texte");
        Check("unknown future pack",label("new-pack.taco")=="Langue à vérifier");
        Check("null filename",label(null)=="Langue à vérifier");
        Func<string,string,string> installed=(f,p)=>(string)language.GetMethod("InstalledLabel").Invoke(null,new object[]{f,p});
        Check("adapted French copy",installed("LadyElyssa.taco",Path.Combine(packs,"Lady-Elyssa-Guides-FR-Classement-des-succes.taco"))=="FR");
        Check("download stays English",label("LadyElyssa.taco")=="US");
        Check("unknown copy not declared French",installed("LadyElyssa.taco",Path.Combine(dir,"Pathing.dll"))==null);
        Check("missing file",installed("LadyElyssa.taco","does-not-exist")==null);
        Check("visibility description",MapVisibilityLevel.Always.Humanize()=="Toujours");
        Check("visibility persistence",MapVisibilityLevel.Always.ToString()=="Always");
        Check("description roundtrip","Toujours".DehumanizeTo<MapVisibilityLevel>()==MapVisibilityLevel.Always);
        Check("clipboard roundtrip","Sur interaction uniquement".DehumanizeTo<MarkerClipboardConsentLevel>()==MarkerClipboardConsentLevel.OnlyWhenInteractedWith);
        Check("popup numeric stability",(int)MarkerInfoDisplayMode.NeverDisplay==100);
        var repo=Newtonsoft.Json.JsonConvert.DeserializeObject<BhModule.Community.Pathing.MarkerPackRepo.MarkerPackPkg[]>(File.ReadAllText(Path.Combine(dir,"repo.json")));
        Check("catalogue coverage",repo.Length==47);
        var urlPattern=new System.Text.RegularExpressions.Regex(@"https?://[^\s]+", System.Text.RegularExpressions.RegexOptions.CultureInvariant);
        foreach(var pack in repo) {
            string original=pack.Description;
            Check("French description "+pack.FileName,!String.IsNullOrWhiteSpace(pack.DisplayDescription)&&pack.DisplayDescription!=original);
            Check("publisher description unchanged "+pack.FileName,pack.Description==original);
            foreach(System.Text.RegularExpressions.Match url in urlPattern.Matches(original))
                Check("publisher link kept "+pack.FileName,pack.DisplayDescription.Contains(url.Value));
            var encoded=Newtonsoft.Json.Linq.JObject.Parse(Newtonsoft.Json.JsonConvert.SerializeObject(pack));
            Check("display-only translation "+pack.FileName,encoded["DisplayDescription"]==null && encoded["DisplayCategories"]==null);
        }
        var hero=repo.Single(p=>p.FileName=="hero.blish.pack.zip");
        Check("Hero translated",hero.DisplayDescription.StartsWith("Ce pack propose"));
        Check("Hero categories translated",hero.DisplayCategories=="Fractales, Raids, Missions d’attaque, Donjons, Configurations, Récolte");
        Check("original categories retained",hero.Categories=="Fractals, Raids, Strike Missions, Dungeons, Builds, Gathering");
        hero.Description="A new publisher description";
        Check("updated publisher text not hidden",hero.DisplayDescription==hero.Description);
        hero.Description=null;hero.Categories=null;
        Check("null description safe",hero.DisplayDescription=="");
        Check("null categories safe",hero.DisplayCategories=="");
        hero.FileName="new-pack.taco";hero.Description="New pack text";hero.Categories="Fractals, New category";
        Check("unknown description retained",hero.DisplayDescription=="New pack text");
        Check("unknown category retained",hero.DisplayCategories=="Fractales, New category");
        var rm=new ResourceManager("BhModule.Community.Pathing.Strings",assembly);
        foreach(var culture in new[]{CultureInfo.InvariantCulture,CultureInfo.GetCultureInfo("fr-FR")}) {
            Check("translated download " + culture.Name,rm.GetString("Repo_Download",culture)=="Télécharger");
            Check("translated options " + culture.Name,rm.GetString("Window_MainSettingsTab",culture)=="Options des marqueurs");
        }
    }
}
