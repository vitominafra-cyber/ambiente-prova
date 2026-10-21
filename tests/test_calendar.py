import base64, io, json, zipfile
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape
import unittest, test_app
from calendar_import import parse_workbook


def workbook():
    b=io.BytesIO()
    ns='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    with zipfile.ZipFile(b,'w') as z:
        z.writestr('xl/workbook.xml',f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Events" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        rows=[['Titolo','Data Inizio','Data Fine','Luogo','Descrizione'],['Evento esterno','2026-11-10T10:00','2026-11-10T18:00','Spazio','<p>Note</p>']]
        xml=''.join('<row r="'+str(i)+'">'+''.join(f'<c r="{col}{i}" t="inlineStr"><is><t>{escape(v)}</t></is></c>' for col,v in zip('ABCDE',r))+'</row>' for i,r in enumerate(rows,1))
        z.writestr('xl/worksheets/sheet1.xml',f'<worksheet xmlns="{ns}"><sheetData>{xml}</sheetData></worksheet>')
    return b.getvalue()

class Calendar(unittest.TestCase):
    setUpClass = classmethod(test_app.Workflow.setUpClass.__func__)
    tearDownClass = classmethod(test_app.Workflow.tearDownClass.__func__)
    lead = test_app.Workflow.lead
    post = test_app.Workflow.post
    def setUp(self):
        test_app.Workflow.setUp(self)
        import app
        with app.connect() as c:c.execute('DELETE FROM external_events')
    def request(self,path,payload):
        with urlopen(Request(self.url+'/api/calendar/'+path,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})) as r:return json.load(r)
    def test_import_dedup_block_remove(self):
        preview=self.request('preview',{'file':base64.b64encode(workbook()).decode()})
        self.assertEqual(len(preview['events']),1)
        self.assertEqual(preview['errors'],[])
        events=preview['events']
        self.assertEqual(self.request('import',{'events':events})['added'],1)
        self.assertEqual(self.request('import',{'events':events})['added'],0)
        self.assertEqual(self.post(self.lead(status='Confermato',signed=True,paid=True))[0],400)
        with urlopen(self.url+'/api/calendar') as r:items=json.load(r)
        self.request('remove',{'key':items[0]['key']})
        self.assertEqual(self.post(self.lead(status='Confermato',signed=True,paid=True))[0],200)
    def test_optional_margin(self):
        event=parse_workbook(workbook())['events'][0];event['buffer']=False
        self.request('import',{'events':[event]})
        self.assertEqual(self.post(self.lead(start='2026-11-11T06:00',end='2026-11-11T10:00',status='Confermato',signed=True,paid=True))[0],200)
