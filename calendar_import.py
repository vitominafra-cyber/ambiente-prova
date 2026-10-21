"""Read the Events workbook without executing formulas or requiring Excel."""
import io, zipfile, re
from datetime import datetime, timedelta
from xml.etree import ElementTree as ET
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}

def parse_workbook(raw):
    if len(raw)>5_000_000: raise ValueError('File troppo grande (massimo 5 MB).')
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        if sum(i.file_size for i in z.infolist())>20_000_000: raise ValueError('Archivio Excel troppo grande.')
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            shared=[''.join(e.itertext()) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        book=ET.fromstring(z.read('xl/workbook.xml'))
        sheets=book.findall('s:sheets/s:sheet',NS)
        sheet=next((s for s in sheets if s.get('name')=='Events'),sheets[0])
        rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
        rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        target=next(x.get('Target') for x in rels if x.get('Id')==rid)
        path=target.lstrip('/') if target.startswith('/') else 'xl/'+target
        epoch=datetime(1904,1,1) if book.find('s:workbookPr',NS) is not None and book.find('s:workbookPr',NS).get('date1904') in ('1','true') else datetime(1899,12,30)
        rows=[]
        for row in ET.fromstring(z.read(path)).findall('s:sheetData/s:row',NS):
            values={}
            for cell in row.findall('s:c',NS):
                col=re.sub(r'\d','',cell.get('r',''))
                if col not in 'ABCDE' or len(col)!=1: continue
                if cell.find('s:f',NS) is not None and cell.find('s:v',NS) is None: raise ValueError('Formula senza valore salvato: esporta il foglio come valori.')
                value=cell.find('s:v',NS); text=value.text if value is not None else ''
                if cell.get('t')=='s':text=shared[int(text)]
                elif cell.get('t')=='inlineStr':text=''.join(cell.find('s:is',NS).itertext())
                values[col]=text
            if any(values.values()):rows.append((int(row.get('r')),values))
        if not rows:raise ValueError('Foglio vuoto.')
        if [rows[0][1].get(c) for c in 'ABCDE']!=['Titolo','Data Inizio','Data Fine','Luogo','Descrizione']:
            raise ValueError('Colonne richieste: Titolo, Data Inizio, Data Fine, Luogo, Descrizione (A–E).')
        events=[]; errors=[]
        def date(v):
            try:return (epoch+timedelta(days=float(v))).isoformat(timespec='minutes')
            except ValueError:return datetime.fromisoformat(v).isoformat(timespec='minutes')
        for number,r in rows[1:]:
            try:
                start,end=date(r.get('B','')),date(r.get('C',''))
                if not r.get('A') or end<=start:raise ValueError('Titolo o date non validi')
                events.append(dict(title=r['A'],start=start,end=end,location=r.get('D',''),description=r.get('E',''),row=number))
            except (ValueError,OverflowError,TypeError):errors.append(f'Riga {number}: titolo o date non validi.')
        return {'events':events,'errors':errors,'sheet':sheet.get('name')}
