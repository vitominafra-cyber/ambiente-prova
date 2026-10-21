import json, sqlite3, os, base64, hashlib
from calendar_import import parse_workbook
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).parent
DB = Path(os.environ.get('EVENTI_DB', str(ROOT / 'eventi.sqlite3')))

def connect():
    c = sqlite3.connect(DB)
    c.execute('CREATE TABLE IF NOT EXISTS leads (id INTEGER PRIMARY KEY, data TEXT NOT NULL)')
    c.execute('CREATE TABLE IF NOT EXISTS external_events (key TEXT PRIMARY KEY, data TEXT NOT NULL)')
    return c

def items(c):
    return [dict(json.loads(d), id=i) for i, d in c.execute('SELECT id,data FROM leads ORDER BY id DESC')]

def external_items(c):
    return [dict(json.loads(d), key=k) for k,d in c.execute("SELECT key,data FROM external_events")]

def interval(d):
    a, b = datetime.fromisoformat(d['start']), datetime.fromisoformat(d['end'])
    if a.tzinfo or b.tzinfo or b <= a:
        raise ValueError('Date non valide: la fine deve essere successiva all’inizio. Usa orari locali senza fuso.')
    buffer = timedelta(hours=12 if d.get('buffer', True) else 0)
    return a - buffer, b + buffer

def overlaps(a, b):
    x, y = interval(a); u, v = interval(b)
    return x < v and u < y

def validate(d):
    if not str(d.get('name', '')).strip() or not str(d.get('event', '')).strip():
        raise ValueError('Nome ed evento sono obbligatori.')
    interval(d)
    if str(d.get('space')) not in ('230', '400'):
        raise ValueError('Seleziona lo spazio da 230 o 400 m².')
    if d.get('status') not in ('Nuovo', 'In trattativa', 'Contratto inviato', 'Confermato', 'Perso'):
        raise ValueError('Stato non valido.')
    if d['status'] == 'Confermato' and not (d.get('signed') and d.get('paid')):
        raise ValueError('Per confermare servono firma e pagamento registrati.')

class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body))); self.end_headers(); self.wfile.write(body)

    def do_GET(self):
        path = urlparse(self.path).path
        if path == '/api/calendar':
            with connect() as c: self.reply(200, external_items(c))
            return
        if path == '/api/leads':
            with connect() as c: self.reply(200, items(c))
            return
        files = {'/': ('index.html','text/html'), '/app.js': ('app.js','text/javascript'), '/style.css': ('style.css','text/css')}
        if path not in files: self.reply(404, {'error':'Non trovato'}); return
        file, mime = files[path]; body = (ROOT / 'static' / file).read_bytes()
        self.send_response(200); self.send_header('Content-Type', mime+'; charset=utf-8'); self.end_headers(); self.wfile.write(body)

    def do_POST(self):
        if self.path in ('/api/calendar/preview','/api/calendar/import','/api/calendar/remove'):
            self.calendar_post(); return
        if self.path != '/api/leads': self.reply(404, {'error':'Non trovato'}); return
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 < length <= 1000000: raise ValueError('Richiesta non valida.')
            d = json.loads(self.rfile.read(length)); validate(d)
            with connect() as c:
                # Serialize availability check and write, so competing confirmations cannot both succeed.
                c.execute('BEGIN IMMEDIATE')
                if d['status'] == 'Confermato':
                    external = [x for x in external_items(c) if overlaps(d,x)]
                    if external: raise ValueError('Date occupate da una voce del calendario importato.')
                    conflicts = [x for x in items(c) if x['id'] != d.get('id') and x['status'] == 'Confermato' and overlaps(d,x)]
                    if conflicts: raise ValueError('Date occupate da un evento confermato, inclusi allestimento e disallestimento.')
                ident = d.pop('id', None)
                if ident:
                    cur = c.execute('UPDATE leads SET data=? WHERE id=?', (json.dumps(d), ident))
                    if not cur.rowcount: raise ValueError('Scheda non trovata.')
                else:
                    ident = c.execute('INSERT INTO leads(data) VALUES (?)', (json.dumps(d),)).lastrowid
            self.reply(200, {'id':ident})
        except (ValueError, TypeError, KeyError, json.JSONDecodeError) as e:
            self.reply(400, {'error':str(e)})

    def calendar_post(self):
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 0<length<=7_000_000:raise ValueError('Dimensione richiesta non valida.')
            payload=json.loads(self.rfile.read(length))
            if self.path.endswith('/preview'):
                result=parse_workbook(base64.b64decode(payload['file'],validate=True))
                self.reply(200,result);return
            with connect() as c:
                if self.path.endswith('/remove'):
                    c.execute('DELETE FROM external_events WHERE key=?',(payload['key'],))
                    self.reply(200,{'removed':True});return
                events=payload['events']
                if not isinstance(events,list) or len(events)>1000:raise ValueError('Elenco eventi non valido.')
                for event in events:
                    interval(event)
                    if not str(event.get('title','')).strip():raise ValueError('Titolo obbligatorio.')
                added=0
                for event in events:
                    key=hashlib.sha256(json.dumps([event['title'],event['start'],event['end']],ensure_ascii=False).encode()).hexdigest()
                    exists=c.execute('SELECT 1 FROM external_events WHERE key=?',(key,)).fetchone()
                    c.execute('INSERT OR REPLACE INTO external_events VALUES (?,?)',(key,json.dumps(event)))
                    added+=not bool(exists)
            self.reply(200,{'added':added,'updated':len(events)-added})
        except Exception as e:
            self.reply(400,{'error':str(e) if isinstance(e,(ValueError,KeyError)) else 'File Excel o richiesta non validi.'})

if __name__ == '__main__':
    connect().close()
    print('Spazio Eventi: http://127.0.0.1:8000', flush=True)
    ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PORT','8000'))), Handler).serve_forever()
