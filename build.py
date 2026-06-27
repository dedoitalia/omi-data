import subprocess, os, glob, json, csv, re, py7zr
from collections import defaultdict

OUT='data'; os.makedirs(OUT, exist_ok=True)
status={'steps':[], 'ok':False}
def log(m):
    status['steps'].append(str(m)); print(m, flush=True)

PROV={'AG':'Agrigento','AL':'Alessandria','AN':'Ancona','AO':'Aosta','AR':'Arezzo','AP':'Ascoli Piceno','AT':'Asti','AV':'Avellino','BA':'Bari','BT':'Barletta-Andria-Trani','BL':'Belluno','BN':'Benevento','BG':'Bergamo','BI':'Biella','BO':'Bologna','BZ':'Bolzano','BS':'Brescia','BR':'Brindisi','CA':'Cagliari','CL':'Caltanissetta','CB':'Campobasso','CE':'Caserta','CT':'Catania','CZ':'Catanzaro','CH':'Chieti','CO':'Como','CS':'Cosenza','CR':'Cremona','KR':'Crotone','CN':'Cuneo','EN':'Enna','FM':'Fermo','FE':'Ferrara','FI':'Firenze','FG':'Foggia','FC':'Forli-Cesena','FR':'Frosinone','GE':'Genova','GO':'Gorizia','GR':'Grosseto','IM':'Imperia','IS':'Isernia','AQ':"L'Aquila",'SP':'La Spezia','LT':'Latina','LE':'Lecce','LC':'Lecco','LI':'Livorno','LO':'Lodi','LU':'Lucca','MC':'Macerata','MN':'Mantova','MS':'Massa-Carrara','MT':'Matera','ME':'Messina','MI':'Milano','MO':'Modena','MB':'Monza e Brianza','NA':'Napoli','NO':'Novara','NU':'Nuoro','OR':'Oristano','PD':'Padova','PA':'Palermo','PR':'Parma','PV':'Pavia','PG':'Perugia','PU':'Pesaro e Urbino','PE':'Pescara','PC':'Piacenza','PI':'Pisa','PT':'Pistoia','PN':'Pordenone','PZ':'Potenza','PO':'Prato','RG':'Ragusa','RA':'Ravenna','RC':'Reggio Calabria','RE':'Reggio Emilia','RI':'Rieti','RN':'Rimini','RM':'Roma','RO':'Rovigo','SA':'Salerno','SS':'Sassari','SV':'Savona','SI':'Siena','SR':'Siracusa','SO':'Sondrio','SU':'Sud Sardegna','TA':'Taranto','TE':'Teramo','TR':'Terni','TO':'Torino','TP':'Trapani','TN':'Trento','TV':'Treviso','TS':'Trieste','UD':'Udine','VA':'Varese','VE':'Venezia','VB':'Verbano-Cusio-Ossola','VC':'Vercelli','VR':'Verona','VV':'Vibo Valentia','VI':'Vicenza','VT':'Viterbo'}

def read_csv(path):
    with open(path, encoding='utf-8', errors='replace') as f:
        sample=f.readline()
    sep=';' if sample.count(';')>=sample.count(',') else ','
    rows=[]
    with open(path, encoding='utf-8', errors='replace') as f:
        r=csv.reader(f, delimiter=sep)
        try: header=next(r)
        except StopIteration: return [], []
        header=[h.strip().strip("'\"") for h in header]
        for row in r:
            if len(row)<2: continue
            rows.append(dict(zip(header, [c.strip().strip("'\"") for c in row])))
    return header, rows

def find(cols, *pats):
    for p in pats:
        for c in cols:
            if re.search(p, c, re.I): return c
    return None

def num(v):
    if not v: return None
    s=re.sub(r'[^0-9,.\-]','', v)
    if not s: return None
    if (',' in s) and ('.' in s): s=s.replace('.','').replace(',','.')
    elif ',' in s: s=s.replace(',','.')
    elif re.match(r'^\d{1,3}(\.\d{3})+$', s): s=s.replace('.','')
    try: return float(s)
    except: return None

try:
    if not os.path.isdir('src'):
        subprocess.run(['git','clone','--depth','1','https://github.com/ondata/quotazioni-immobiliari-agenzia-entrate','src'], check=True)
    log('cloned ondata')
    os.makedirs('ex', exist_ok=True)
    for z in glob.glob('src/**/*.7z', recursive=True):
        try:
            with py7zr.SevenZipFile(z,'r') as a: a.extractall('ex')
            log('extracted '+z)
        except Exception as e: log('extract fail '+z+': '+str(e))
    csvs=glob.glob('ex/**/*.csv', recursive=True)+glob.glob('src/**/*.csv', recursive=True)
    log('csv: '+', '.join(csvs[:20]))
    valori=zona=None
    for c in csvs:
        try: h,_=read_csv(c)
        except Exception: continue
        hl=' '.join(h).lower()
        if 'compr' in hl and valori is None: valori=c
        if re.search(r'zona.?desc|descr.?zona|microzona', hl) and zona is None: zona=c
    log('valori='+str(valori)+' zona='+str(zona))
    if not valori: raise RuntimeError('no valori csv found')
    vh, vrows = read_csv(valori)
    log('valori rows='+str(len(vrows))+' cols='+str(vh))
    kProv=find(vh, r'^prov$', r'prov'); kComune=find(vh, r'comune.?desc', r'comune.?amm', r'comune')
    kZona=find(vh, r'zona.?desc', r'^zona$', r'zona'); kFascia=find(vh, r'fascia')
    kLink=find(vh, r'linkzona', r'link'); kTip=find(vh, r'descr.?tip', r'tipolog')
    kCmin=find(vh, r'compr.?min'); kCmax=find(vh, r'compr.?max')
    kLmin=find(vh, r'loc.?min'); kLmax=find(vh, r'loc.?max')
    status['cols']={'prov':kProv,'comune':kComune,'zona':kZona,'fascia':kFascia,'link':kLink,'tip':kTip,'cmin':kCmin,'cmax':kCmax,'lmin':kLmin,'lmax':kLmax}
    log('cols '+json.dumps(status['cols']))
    zdesc={}
    if zona:
        zh, zrows = read_csv(zona)
        zC=find(zh, r'comune.?desc', r'comune'); zL=find(zh, r'linkzona', r'link', r'^zona$'); zD=find(zh, r'zona.?desc', r'descr.?zona', r'microzona')
        if zC and zL and zD:
            for r in zrows: zdesc[(r.get(zC,'').upper(), r.get(zL,''))]=r.get(zD,'')
        log('zona descr entries='+str(len(zdesc)))
    byprov=defaultdict(list)
    for r in vrows:
        prov=(r.get(kProv,'') or 'XX').strip().upper()
        comune=(r.get(kComune,'') or '').strip()
        link=r.get(kLink,'') if kLink else ''
        zcode=(r.get(kZona,'') if kZona else '') or ''
        zd=zdesc.get((comune.upper(), link)) if zdesc else None
        zlabel=zd or (r.get(kFascia,'') if kFascia else '') or zcode or ''
        cmin=num(r.get(kCmin,'')) if kCmin else None; cmax=num(r.get(kCmax,'')) if kCmax else None
        if not (cmin or cmax): continue
        byprov[prov].append({'comune':comune,'zona':zlabel,'tipo':(r.get(kTip,'') if kTip else ''),
            'compr_min':cmin,'compr_max':cmax,
            'loc_min':num(r.get(kLmin,'')) if kLmin else None,'loc_max':num(r.get(kLmax,'')) if kLmax else None})
    index=[]
    for prov, recs in byprov.items():
        name=PROV.get(prov, prov); fn=name+'.json'
        with open(os.path.join(OUT, fn),'w',encoding='utf-8') as f: json.dump(recs, f, ensure_ascii=False)
        index.append({'prov':prov,'name':name,'file':fn,'records':len(recs)})
    index.sort(key=lambda x:x['name'])
    with open(os.path.join(OUT,'index.json'),'w',encoding='utf-8') as f: json.dump(index, f, ensure_ascii=False)
    status['provinces']=len(index); status['total_records']=sum(i['records'] for i in index); status['ok']=True
    log('DONE provinces='+str(len(index)))
except Exception as e:
    status['error']=repr(e); log('ERROR '+repr(e))
with open(os.path.join(OUT,'_status.json'),'w',encoding='utf-8') as f: json.dump(status, f, ensure_ascii=False, indent=1)
print(json.dumps(status)[:1500], flush=True)
