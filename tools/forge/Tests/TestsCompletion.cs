using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using BhModule.Community.Pathing.Utility;
class TestsCompletion {
    static int count;
    static void Check(string name, bool value) { if (!value) throw new Exception("FAIL " + name); count++; }
    static int Main(string[] args) {
        try {
            var known = new HashSet<int> { 1, 2, 3, 4 };
            var repeat = new HashSet<int> { 3 };
            Func<int, bool?> done = id => id == 1 || id == 3 ? true : id == 2 ? false : (bool?)null;
            Func<int[], bool, bool> finish = (ids, fresh) => CompletionPolicy.AllFinished(ids, known, repeat, done, fresh);
            Check("completed nonrepeatable", finish(new[] {1}, true));
            Check("in progress", !finish(new[] {2}, true));
            Check("repeatable already completed", !finish(new[] {3}, true));
            Check("unknown account status", !finish(new[] {4}, true));
            Check("unknown definition", !finish(new[] {99}, true));
            Check("no proof", !finish(new int[0], true));
            Check("null scope", !finish(null, true));
            Check("unavailable API", !finish(new[] {1}, false));
            Check("partial group", !finish(new[] {1,2}, true));
            Check("group containing repeatable", !finish(new[] {1,3}, true));
            Check("group containing unknown", !finish(new[] {1,99}, true));
            Check("duplicate ids", finish(new[] {1,1}, true));
            Check("fully completed group", CompletionPolicy.AllFinished(new[]{1,2},known,repeat,id=>true,true));
            var lines = File.ReadAllLines(args[0]);
            var actualKnown = new HashSet<int>(lines[0].Split(',').Select(int.Parse));
            var actualRepeat = new HashSet<int>(lines[1].Split(',').Select(int.Parse));
            foreach (int id in actualRepeat) Check("official repeatable " + id,
                !CompletionPolicy.AllFinished(new[]{id}, actualKnown, actualRepeat, x=>true, true));
            foreach(int id in new[]{6219,6239,6369,7053,7126,7809}) {
                Check("lantern metadata " + id, actualRepeat.Contains(id));
                Check("lantern available " + id, !CompletionPolicy.AllFinished(new[]{id},actualKnown,actualRepeat,x=>true,true));
            }
            Console.WriteLine("PASS " + count + " assertions (13 scenarios, all " + actualRepeat.Count + " repeatable definitions, 6 lantern routes)");
            return 0;
        } catch(Exception e) { Console.Error.WriteLine(e.Message); return 1; }
    }
}