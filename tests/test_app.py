import json, tempfile, threading, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import app

class Workflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory();app.DB=Path(cls.tmp.name)/'test.sqlite3'
        cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.url='http://127.0.0.1:'+str(cls.server.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.tmp.cleanup()
    def setUp(self):
        with app.connect() as c:c.execute('DELETE FROM leads')
    def post(self,d):
        req=Request(self.url+'/api/leads',data=json.dumps(d).encode(),headers={'Content-Type':'application/json'})
        try:
            with urlopen(req) as r:return r.status,json.load(r)
        except HTTPError as e:return e.code,json.load(e)
    def lead(self,**kw):
        return dict(dict(name='Cliente',event='Evento',start='2026-11-10T10:00',end='2026-11-10T18:00',space='230',status='Nuovo',signed=False,paid=False),**kw)
    def test_save_read_update(self):
        code,res=self.post(self.lead());self.assertEqual(code,200)
        with urlopen(self.url+'/api/leads') as r:self.assertEqual(json.load(r)[0]['event'],'Evento')
        self.assertEqual(self.post(self.lead(id=res['id'],event='Modificato'))[0],200)
        with urlopen(self.url+'/api/leads') as r:self.assertEqual(json.load(r)[0]['event'],'Modificato')
    def test_confirmation_requires_both(self):
        for flags in ({},{'signed':True},{'paid':True}):
            self.assertEqual(self.post(self.lead(status='Confermato',**flags))[0],400)
    def test_buffer_and_conflict(self):
        self.assertEqual(self.post(self.lead(status='Confermato',signed=True,paid=True))[0],200)
        self.assertEqual(self.post(self.lead(start='2026-11-11T10:00',end='2026-11-11T18:00',status='Confermato',signed=True,paid=True))[0],400)
        self.assertEqual(self.post(self.lead(start='2026-11-11T18:00',end='2026-11-11T22:00',status='Confermato',signed=True,paid=True))[0],200)
    def test_competing_leads_allowed(self):
        self.assertEqual(self.post(self.lead())[0],200)
        self.assertEqual(self.post(self.lead())[0],200)
    def test_invalid_dates(self):
        self.assertEqual(self.post(self.lead(end='2026-11-09T10:00'))[0],400)
    def test_page_and_assets(self):
        for p in ['/','/app.js','/style.css']:
            with urlopen(self.url+p) as r:self.assertEqual(r.status,200);self.assertGreater(len(r.read()),100)
    def test_concurrent_confirmations(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.post(self.lead(status='Confermato',signed=True,paid=True))[0],range(2)))
        self.assertEqual(sorted(results),[200,400])

if __name__=='__main__':unittest.main()
