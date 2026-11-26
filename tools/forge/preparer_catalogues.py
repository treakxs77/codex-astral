"""Build French public catalogues with reviewed memory and a local EN->FR model.
No account, password or player API key is processed. Never changes download URLs or hashes.
"""
from pathlib import Path
import argparse, gzip, json, re, urllib.request
import ctranslate2, sentencepiece

ROOT=Path(__file__).resolve().parent
SAFE=re.compile(r'https?://[^\s<>]+|\{[^{}]*\}|%\d*\$?[sdf]|<[^>]+>|\b(?:Blish HUD|Guild Wars 2|GW2|ArcDPS|TacO|Twitch|ChatGPT|ArenaNet|Pathing|Heart of Thorns|Path of Fire|End of Dragons|Secrets of the Obscure|Janthir Wilds|Visions of Eternity)\b')

def normalize(s): return re.sub(r'\s+',' ',s or '').strip()

class Translator:
    def __init__(self,model,memory):
        self.sp=sentencepiece.SentencePieceProcessor(model_file=str(model/'sentencepiece.model'))
        self.engine=ctranslate2.Translator(str(model/'model'),device='cpu',compute_type='int8',intra_threads=4)
        self.file=memory;self.memory=json.loads(memory.read_text(encoding='utf-8')) if memory.exists() else {}
        self.memory={key:value.replace('▁',' ') for key,value in self.memory.items()}
    def translate_many(self,texts):
        segments=[]
        for text in texts:
            if not text or text in self.memory:continue
            for part in re.split('('+SAFE.pattern+')',text):
                if part.strip() and not SAFE.fullmatch(part) and re.search('[A-Za-z]{2}',part) and part not in self.memory:segments.append(part)
        segments=list(dict.fromkeys(segments))
        for offset in range(0,len(segments),12):
            batch=segments[offset:offset+12]
            encoded=[self.sp.encode(s.strip(),out_type=str) for s in batch]
            results=self.engine.translate_batch(encoded,beam_size=3,max_input_length=0,max_decoding_length=768)
            for source,result in zip(batch,results):
                target=self.sp.decode(result.hypotheses[0]).replace('▁',' ').strip()
                if not target:raise ValueError('Traduction vide')
                self.memory[source]=(' ' if source.startswith(' ') else '')+target+(' ' if source.endswith(' ') else '')
            self.save();print(f'Traduction locale : {min(offset+12,len(segments))}/{len(segments)} segments',flush=True)
        for text in texts:
            if not text or text in self.memory:continue
            parts=re.split('('+SAFE.pattern+')',text)
            result=''.join(self.memory.get(p,p) for p in parts)
            if SAFE.findall(result)!=SAFE.findall(text):raise ValueError('Lien ou variable altéré')
            self.memory[text]=result
        self.save()
    def save(self):self.file.parent.mkdir(parents=True,exist_ok=True);self.file.write_text(json.dumps(self.memory,ensure_ascii=False,indent=2),encoding='utf-8')

def main():
    p=argparse.ArgumentParser();p.add_argument('--modules',type=Path,required=True);p.add_argument('--markers',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--model',type=Path,required=True);a=p.parse_args()
    modules=json.loads(a.modules.read_text(encoding='utf-8-sig'));markers=json.loads(a.markers.read_text(encoding='utf-8-sig'))
    translator=Translator(a.model,ROOT/'memoire-en-fr.json')
    reviewed=ROOT/'descriptifs-verifies.json'
    existing=json.loads(reviewed.read_text(encoding='utf-8-sig'))
    descriptions=existing.get('Descriptions',{})
    for entry in descriptions.values():
        if entry.get('Source') and entry.get('French'):translator.memory[entry['Source']]=entry['French']
    translator.translate_many(list(dict.fromkeys([m.get('description','') for m in modules]+[m.get('Description','') for m in markers]+[m.get('Categories','') for m in markers])))
    originals=[(m.get('location'),m.get('hash'),m.get('namespace'),m.get('version')) for m in modules]
    for module in modules:module['description']=translator.memory.get(module.get('description',''),module.get('description',''))
    for marker in markers:
        original=marker.get('Description','');marker['Description']=translator.memory.get(original,original)
        marker['Categories']=translator.memory.get(marker.get('Categories',''),marker.get('Categories',''))
    if originals!=[(m.get('location'),m.get('hash'),m.get('namespace'),m.get('version')) for m in modules]:raise ValueError('Catalogue de téléchargement modifié')
    a.output.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(modules,ensure_ascii=False,indent=2).encode('utf-8')
    (a.output/'packages.json').write_bytes(raw);(a.output/'packages.gz').write_bytes(gzip.compress(raw,mtime=0))
    (a.output/'repo-fr.json').write_text(json.dumps(markers,ensure_ascii=False,indent=2),encoding='utf-8')
    (a.output/'validation-textes.json').write_text(json.dumps({'modules':len(modules),'markers':len(markers),'links_and_hashes_unchanged':True,'automatic_translation':True},indent=2),encoding='utf-8')
    print('Catalogues français prêts, liens et empreintes conservés.',flush=True)

if __name__=='__main__':main()
