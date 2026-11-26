"""Translate textual TacO attributes; preserve identifiers, coordinates, assets and trails."""
from pathlib import Path
import argparse, hashlib, json, re, zipfile, xml.etree.ElementTree as ET
from preparer_catalogues import Translator

TEXT={'displayname','tip-name','tip-description','tipname','tipdescription','title','text','info','description'}

def xml(data):
    if b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper():raise ValueError('DTD interdite')
    return ET.fromstring(data)

def index(root):
    result={}
    def walk(node,path=''):
        tag=node.tag.lower()
        if tag=='markercategory':
            path=(path+'.'+node.attrib.get('name','')).strip('.');key='category:'+path.lower()
        elif node.attrib.get('guid') or node.attrib.get('GUID'):
            key='guid:'+node.attrib.get('guid',node.attrib.get('GUID',''))
        else:key=None
        if key:result.setdefault(key,[]).append(node)
        for child in node:walk(child,path)
    walk(root);return result

def pack_index(path):
    result={}
    with zipfile.ZipFile(path) as z:
        for e in z.infolist():
            if not e.filename.lower().endswith('.xml'):continue
            if e.file_size>268435456:raise ValueError('XML trop volumineux')
            data=z.read(e)
            try:document=xml(data)
            except ET.ParseError as error:
                if 'duplicate attribute' not in str(error):raise
                # Text-memory extraction only. Do not change or republish this publisher XML.
                def repair(match):
                    seen=set()
                    def attribute(a):
                        key=a.group(1).lower()
                        if key in seen:
                            if key in TEXT or key in {'name','guid'}:raise ValueError('Identité ou texte ambigu dans le pack')
                            return ''
                        seen.add(key);return a.group()
                    return re.sub(r'([\w-]+)\s*=\s*("[^"]*"|\x27[^\x27]*\x27)',attribute,match.group())
                document=xml(re.sub(r'<[^!?][^>]*>',repair,data.decode('utf-8-sig')).encode('utf-8'))
            for key,nodes in index(document).items():result.setdefault(key,[]).extend(nodes)
    return result

def seed(original,french,memory):
    en,fr=pack_index(original),pack_index(french);entries={}
    for key,nodes in en.items():
        target=fr.get(key)
        if not target:continue
        # Only reuse a value whose definition is unambiguous across the pack.
        for attr in TEXT:
            sources={n.attrib[attr] for n in nodes if attr in n.attrib};targets={n.attrib[attr] for n in target if attr in n.attrib}
            if len(sources)==1 and len(targets)==1:entries[key+'|'+attr]={'Source':sources.pop(),'French':targets.pop()}
        for n in target:
            for attr,value in n.attrib.items():
                if attr.startswith('completion-'):entries[key+'|'+attr]={'Value':value}
    memory.write_text(json.dumps(entries,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    return len(entries)

def translate(original,output,memory,model,version):
    saved=json.loads(memory.read_text(encoding='utf-8')) if memory.exists() else {}
    translator=Translator(model,memory.with_name(memory.stem+'-text.json'));documents={};needed=[];preserved=0
    with zipfile.ZipFile(original) as z:
        for entry in z.infolist():
            if not entry.filename.lower().endswith('.xml'):continue
            if entry.file_size>268435456:raise ValueError('XML trop volumineux')
            root=xml(z.read(entry));documents[entry.filename]=root
            identified={id(node):key for key,nodes in index(root).items() for node in nodes}
            for node in root.iter():
                key=identified.get(id(node),'')
                for attr,source in list(node.attrib.items()):
                    if attr.lower() not in TEXT:continue
                    old=saved.get(key+'|'+attr)
                    if old and old.get('Source')==source:node.attrib[attr]=old['French'];preserved+=1
                    else:needed.append(source)
                for attr in ['completion-track','completion-source','completion-id']:
                    old=saved.get(key+'|'+attr)
                    if old and 'Value' in old:node.attrib[attr]=old['Value']
        translator.translate_many(needed)
        with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as target:
            for entry in z.infolist():
                if entry.is_dir():continue
                if entry.filename not in documents:target.writestr(entry,z.read(entry));continue
                root=documents[entry.filename];identified={id(n):k for k,ns in index(root).items() for n in ns}
                original_nodes=list(xml(z.read(entry)).iter());nodes=list(root.iter())
                if len(original_nodes)!=len(nodes):raise ValueError('Structure du pack modifiée')
                for before,node in zip(original_nodes,nodes):
                    key=identified.get(id(node),'')
                    for attr,source in before.attrib.items():
                        if attr.lower() in TEXT:
                            old=saved.get(key+'|'+attr)
                            node.attrib[attr]=old['French'] if old and old.get('Source')==source else translator.memory.get(source,source)
                            saved[key+'|'+attr]={'Source':source,'French':node.attrib[attr]}
                        elif node.attrib.get(attr)!=source:raise ValueError('Attribut fonctionnel modifié : '+attr)
                target.writestr(entry,ET.tostring(root,encoding='utf-8',xml_declaration=True))
            target.writestr('_forge-translation.json',json.dumps({'Version':version,'Language':'fr','OriginalHash':hashlib.sha256(Path(original).read_bytes()).hexdigest(),'Automatic':True,'Preserved':preserved,'Translated':len(set(needed))}))
    memory.write_text(json.dumps(saved,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    # Every non-XML asset must remain byte-for-byte identical.
    with zipfile.ZipFile(original) as a,zipfile.ZipFile(output) as b:
        for e in a.infolist():
            if not e.is_dir() and not e.filename.lower().endswith('.xml') and a.read(e)!=b.read(e.filename):raise ValueError('Ressource binaire modifiée')
    return {'preserved':preserved,'translated':len(set(needed)),'functional_attributes_unchanged':True,'assets_unchanged':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['seed','translate']);p.add_argument('--original',type=Path,required=True);p.add_argument('--french',type=Path);p.add_argument('--memory',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--model',type=Path);p.add_argument('--version',default='');a=p.parse_args()
    print(seed(a.original,a.french,a.memory) if a.action=='seed' else translate(a.original,a.output,a.memory,a.model,a.version),flush=True)
