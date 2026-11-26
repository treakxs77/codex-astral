"""Unattended publisher for the curated French Blish/marker catalogue.
Run only on the maintainer machine or the dedicated GitHub Actions runner.
Player installations are never accessed. Feed is published last, after validation.
"""
from pathlib import Path
import argparse, datetime, gzip, hashlib, json, os, re, shutil, subprocess, sys, urllib.request, zipfile
import xml.etree.ElementTree as ET
from preparer_catalogues import Translator
from traduire_pack import translate

ROOT=Path(__file__).resolve().parent
FEED_BASE='https://github.com/treakxs77/codex-astral/releases/download/forge-traductions/'
PACKS={'tw_ALL_IN_ONE.taco':'Tekkit-All-In-One-FR-Classement-des-succes.taco','LadyElyssa.taco':'Lady-Elyssa-Guides-FR-Classement-des-succes.taco','LadyElyssaAP.taco':'Lady-Elyssa-Succes-et-Collections-FR-Classement-des-succes.taco','TehsTrails.taco':'Tehs-Trails-FR-Classement-des-succes.taco'}

def get(url,path):
    if not url.startswith('https://'):raise ValueError('HTTPS requis')
    path.parent.mkdir(parents=True,exist_ok=True)
    with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Codex-Astral-Forge'}),timeout=120) as r,path.open('wb') as out:shutil.copyfileobj(r,out)
    return path

def data(url,path):return json.loads(get(url,path).read_text(encoding='utf-8-sig'))
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def version(text):return tuple(map(int,text.lstrip('v').split('.'))) if re.fullmatch(r'v?\d+\.\d+\.\d+(\.\d+)?',text or '') else ()
def extract(archive,folder):
    folder=folder.resolve()
    with zipfile.ZipFile(archive) as z:
        for e in z.infolist():
            target=(folder/e.filename).resolve()
            if target!=folder and folder not in target.parents:raise ValueError('Chemin interdit dans une archive')
        z.extractall(folder)

def model(work):
    local=list((ROOT/'Modeles/en_fr').glob('*/sentencepiece.model'))
    if local:return local[0].parent
    package=get('https://data.argosopentech.com/argospm/v1/translate-en_fr-1_9.argosmodel',work/'en_fr.argosmodel');extract(package,work/'model');return next((work/'model').glob('*/sentencepiece.model')).parent

def recipe(id,kind,ver,original,original_hash,french):
    return {'Id':id,'Kind':kind,'Version':ver,'OriginalUrl':original,'OriginalHash':original_hash,'FrenchUrl':FEED_BASE+french.name,'FrenchHash':digest(french),'Ready':True}

def pathing(latest,work,out,modeldir):
    ver=latest['version'];official=get(latest['location'],work/'Pathing-officiel.bhm')
    if digest(official)!=latest['hash'].lower():raise ValueError('Empreinte officielle Pathing incorrecte')
    repo=data('https://api.github.com/repos/blish-hud/Pathing',work/'pathing-repo.json');branch=repo['default_branch']
    commit=data('https://api.github.com/repos/blish-hud/Pathing/commits/'+branch,work/'pathing-commit.json')['sha']
    archive=get('https://codeload.github.com/blish-hud/Pathing/zip/'+commit,work/'source.zip');extract(archive,work/'source');source=next((work/'source').iterdir())
    if json.loads((source/'manifest.json').read_text(encoding='utf-8-sig'))['version']!=ver:raise ValueError('Les sources ne correspondent pas au module publié')
    git_env={**os.environ,'GIT_CEILING_DIRECTORIES':str(source.parent.resolve())}
    subprocess.run(['git','apply','--check','--ignore-whitespace','--whitespace=nowarn',str(ROOT/'pathing-fr.patch')],cwd=source,env=git_env,check=True)
    subprocess.run(['git','apply','--ignore-whitespace','--whitespace=nowarn',str(ROOT/'pathing-fr.patch')],cwd=source,env=git_env,check=True)
    if 'CompletionUtil.IsCompleted' not in (source/'UI/Controls/NodeTree/PathingCategoryNode.cs').read_text(encoding='utf-8-sig'):raise ValueError('Adaptation Pathing non appliquée')
    memory=json.loads((ROOT/'pathing-strings.json').read_text(encoding='utf-8'));tree=ET.parse(source/'Strings.resx');translator=Translator(modeldir,ROOT/'memoire-en-fr.json');needed=[]
    for entry in tree.getroot().findall('data'):
        original=entry.findtext('value');old=memory.get(entry.get('name'))
        if not old or old['Source']!=original:needed.append(original)
    translator.translate_many(needed)
    for entry in tree.getroot().findall('data'):
        original=entry.findtext('value');old=memory.get(entry.get('name'));entry.find('value').text=old['French'] if old and old['Source']==original else translator.memory[original]
    for name in ['Strings.resx','Strings.fr.resx']:tree.write(source/name,encoding='utf-8',xml_declaration=True)
    host=data('https://api.github.com/repos/blish-hud/Blish-HUD/releases/latest',work/'blish.json');assets=[a for a in host['assets'] if a['name'].lower().endswith('.zip')]
    if len(assets)!=1:raise ValueError('Archive Blish HUD ambiguë')
    extract(get(assets[0]['browser_download_url'],work/'blish.zip'),work/'blish');exe=next((work/'blish').rglob('Blish HUD.exe'))
    compilation=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Compiler-Pathing.ps1'),'-SourceDirectory',str(source),'-OfficialPackage',str(official),'-OutputDirectory',str(out),'-Version',ver,'-BlishExe',str(exe)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (work/'compilation.log').write_text(compilation.stdout+'\n'+compilation.stderr,encoding='utf-8')
    if compilation.returncode:raise RuntimeError('Compilation Pathing impossible ; voir compilation.log')
    french=out/f'Pathing-{ver}-FR-Descriptifs-Termines.bhm'
    with zipfile.ZipFile(french) as z:
        manifest=json.loads(z.read('manifest.json').decode('utf-8-sig'))
        if manifest['version']!=ver or manifest['namespace']!='bh.community.pathing' or 'Pathing.dll' not in z.namelist():raise ValueError('Module français invalide')
    prior=data(FEED_BASE+'catalogue-fr.json',work/'tests-feed.json');packs=work/'tests-packs';packs.mkdir(exist_ok=True)
    for id,file in PACKS.items():
        r=next(r for r in prior['Releases'] if r['Id']==id);target=get(r['FrenchUrl'],packs/file)
        if digest(target)!=r['FrenchHash']:raise ValueError('Pack de référence incorrect')
    checks=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'Verifier-Preparation.ps1'),'-SourceDirectory',str(source),'-BuildDirectory',str(out/'Build'),'-PayloadDirectory',str(packs)],capture_output=True,text=True,encoding='utf-8',errors='replace')
    (work/'tests.log').write_text(checks.stdout+'\n'+checks.stderr,encoding='utf-8')
    if checks.returncode:raise RuntimeError('Tests Pathing échoués ; voir tests.log')
    return recipe('bh.community.pathing','modules',ver,latest['location'],latest['hash'].lower(),french)

def main():
    p=argparse.ArgumentParser();p.add_argument('--seed',action='store_true');p.add_argument('--publish',action='store_true');p.add_argument('--payload',type=Path);p.add_argument('--work',type=Path,default=ROOT/'Travail');p.add_argument('--output',type=Path,default=ROOT/'Distribution');a=p.parse_args()
    work=a.work.resolve();out=a.output.resolve();work.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    modules=data('https://pkgs.blishhud.com/packages.json',work/'modules.json');markers=data('https://mp-repo.blishhud.com/repo.json',work/'markers.json')
    previous={};releases=[];pending=[]
    if not a.seed:
        old=data(FEED_BASE+'catalogue-fr.json',work/'previous.json');previous={r['Id']:r for r in old['Releases']}
        for name in ['memoire-en-fr.json','memoires.zip']:
            try:get(FEED_BASE+name,work/name)
            except Exception:continue
        if (work/'memoire-en-fr.json').exists():shutil.copyfile(work/'memoire-en-fr.json',ROOT/'memoire-en-fr.json')
        if (work/'memoires.zip').exists():extract(work/'memoires.zip',ROOT/'Memoires')
    m=model(work)
    for id,file in PACKS.items():
        latest=next(r for r in markers if r['FileName']==id)
        try:
            if a.seed:
                french=out/file;shutil.copyfile(a.payload/file,french);original=get(latest['Download'],work/id)
                releases.append(recipe(id,'markers',latest['Version'],latest['Download'],digest(original),french))
            elif id in previous and previous[id]['Version']==latest['Version']:releases.append(previous[id])
            else:
                original=get(latest['Download'],work/id);safe=re.sub('[^A-Za-z0-9._-]','_',latest['Version']);french=out/(Path(id).stem+'-FR-'+safe+'.taco')
                translate(original,french,ROOT/'Memoires'/(id+'.json'),m,latest['Version']);releases.append(recipe(id,'markers',latest['Version'],latest['Download'],digest(original),french))
        except Exception as ex:
            pending.append({'Id':id,'Version':latest['Version'],'Reason':str(ex)});print('::warning::'+id+' : '+str(ex),flush=True)
            if id in previous:releases.append(previous[id])
    latest=max((r for r in modules if r['namespace']=='bh.community.pathing' and version(r['version'])),key=lambda r:version(r['version']))
    try:
        if a.seed:
            french=out/('Pathing-'+latest['version']+'-FR-Descriptifs-Termines.bhm');shutil.copyfile(a.payload/french.name,french);releases.append(recipe('bh.community.pathing','modules',latest['version'],latest['location'],latest['hash'].lower(),french))
        elif previous.get('bh.community.pathing',{}).get('Version')==latest['version']:releases.append(previous['bh.community.pathing'])
        else:releases.append(pathing(latest,work,out,m))
    except Exception as ex:
        pending.append({'Id':'bh.community.pathing','Version':latest['version'],'Reason':str(ex)});print('::warning::Pathing : '+str(ex),flush=True)
        if 'bh.community.pathing' in previous:releases.append(previous['bh.community.pathing'])
    subprocess.run([sys.executable,str(ROOT/'preparer_catalogues.py'),'--modules',str(work/'modules.json'),'--markers',str(work/'markers.json'),'--output',str(out),'--model',str(m)],check=True)
    curated=next((r for r in releases if r['Id']=='bh.community.pathing' and r['Ready']),None)
    translated=json.loads((out/'packages.json').read_text(encoding='utf-8'))
    if curated:
        translated=[r for r in translated if r['namespace']!='bh.community.pathing' or r['version']==curated['Version']]
        for r in translated:
            if r['namespace']=='bh.community.pathing':r['location']=curated['FrenchUrl'];r['hash']=curated['FrenchHash'];r['name']='Pathing · Français et Terminés'
    raw=json.dumps(translated,ensure_ascii=False,indent=2).encode('utf-8');(out/'packages.json').write_bytes(raw);(out/'packages.gz').write_bytes(gzip.compress(raw,mtime=0))
    (out/'preview-packages.gz').write_bytes(gzip.compress(b'[]',mtime=0));(out/'preview-packages.json').write_text('[]',encoding='utf-8')
    shutil.copyfile(ROOT/'memoire-en-fr.json',out/'memoire-en-fr.json')
    with zipfile.ZipFile(out/'memoires.zip','w',zipfile.ZIP_DEFLATED) as z:
        for file in (ROOT/'Memoires').glob('*.json'):z.write(file,file.name)
    feed={'Schema':1,'CatalogueReady':True,'GeneratedUtc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'Releases':releases,'Pending':pending}
    (out/'catalogue-fr.json').write_text(json.dumps(feed,ensure_ascii=False,indent=2),encoding='utf-8')
    if a.publish:
        gh=shutil.which('gh') or str(ROOT.parents[0]/'Outils/GitHubCLI/bin/gh.exe');repo='treakxs77/codex-astral'
        exists=subprocess.run([gh,'release','view','forge-traductions','--repo',repo],capture_output=True).returncode==0
        if not exists:subprocess.run([gh,'release','create','forge-traductions','--repo',repo,'--title','Catalogue français de la Forge','--notes','Traductions des modules et packs gérées séparément des mises à jour du Codex.','--latest=false','--prerelease'],check=True)
        assets=[str(p) for p in out.iterdir() if p.is_file() and p.name!='catalogue-fr.json']
        for offset in range(0,len(assets),8):subprocess.run([gh,'release','upload','forge-traductions','--repo',repo,'--clobber',*assets[offset:offset+8]],check=True)
        subprocess.run([gh,'release','upload','forge-traductions','--repo',repo,'--clobber',str(out/'catalogue-fr.json')],check=True)
    print(json.dumps({'ready':len(releases),'pending':len(pending),'published':a.publish}),flush=True)

if __name__=='__main__':main()
