from pathlib import Path
import json,tempfile,unittest,zipfile
from unittest.mock import patch
import traduire_pack
from preparer_catalogues import SAFE

class FakeTranslator:
    def __init__(self,*args):self.memory={}
    def translate_many(self,texts):self.memory.update({text:'FR '+text for text in texts})

class Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def pack(self,name,text):
        file=self.root/name
        with zipfile.ZipFile(file,'w') as z:z.writestr(name+'.xml',text);z.writestr('trail.trl',b'BINARY-TRAIL-UNCHANGED')
        return file
    def test_memory_across_xml_names(self):
        en=self.pack('original.taco','<overlaydata><markercategory name="a" displayname="Hello"/></overlaydata>')
        fr=self.pack('fr.taco','<overlaydata><markercategory name="a" displayname="Bonjour" completion-track="true"/></overlaydata>');memory=self.root/'memory.json'
        self.assertEqual(traduire_pack.seed(en,fr,memory),2)
        with patch('traduire_pack.Translator',FakeTranslator):report=traduire_pack.translate(en,self.root/'out.taco',memory,self.root,'v1')
        self.assertTrue(report['assets_unchanged']);self.assertEqual(report['preserved'],1)
        with zipfile.ZipFile(self.root/'out.taco') as z:
            root=traduire_pack.xml(z.read('original.taco.xml'));category=root[0];self.assertEqual(category.attrib['displayname'],'Bonjour');self.assertEqual(category.attrib['completion-track'],'true');self.assertEqual(category.attrib['name'],'a');self.assertEqual(z.read('trail.trl'),b'BINARY-TRAIL-UNCHANGED')
    def test_changed_source_is_retranslated(self):
        en=self.pack('new.taco','<overlaydata><markercategory name="a" displayname="New instructions" mapid="12" xpos="34.5"/></overlaydata>');memory=self.root/'memory.json';memory.write_text(json.dumps({'category:a|displayname':{'Source':'Old instructions','French':'Anciennes consignes'}}))
        with patch('traduire_pack.Translator',FakeTranslator):traduire_pack.translate(en,self.root/'out.taco',memory,self.root,'v2')
        with zipfile.ZipFile(self.root/'out.taco') as z:
            node=traduire_pack.xml(z.read('new.taco.xml'))[0];self.assertEqual(node.attrib['displayname'],'FR New instructions');self.assertEqual(node.attrib['mapid'],'12');self.assertEqual(node.attrib['xpos'],'34.5')
    def test_dtd_is_rejected(self):
        with self.assertRaises(ValueError):traduire_pack.xml(b'<!DOCTYPE overlaydata><overlaydata/>')
    def test_ambiguous_publisher_xml_is_not_republished(self):
        en=self.pack('bad.taco','<overlaydata><markercategory name="a" mapid="1" mapid="2"/></overlaydata>')
        with patch('traduire_pack.Translator',FakeTranslator),self.assertRaises(Exception):traduire_pack.translate(en,self.root/'out.taco',self.root/'memory.json',self.root,'v3')
        self.assertFalse((self.root/'out.taco').exists())
    def test_urls_variables_and_brands_are_protected(self):
        text='Blish HUD https://example.test/path?q=2 {0} %s <b>Guild Wars 2</b>'
        self.assertEqual(SAFE.findall(text),['Blish HUD','https://example.test/path?q=2','{0}','%s','<b>','Guild Wars 2','</b>'])

if __name__=='__main__':unittest.main()
