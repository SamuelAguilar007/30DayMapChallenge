"""Rebuild with Python standard library; run from the parent workspace."""
import zipfile,struct,csv,collections,json,math,unicodedata,hashlib,pathlib,sys
from inspect_data import dbf
ROOT=pathlib.Path(__file__).parent.parent; OUT=ROOT/'data'; INPUT=pathlib.Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'entrada'; OUT.mkdir(exist_ok=True)
def repair(s):
 try: return s.encode('latin1').decode('utf8') if 'Ã' in s else s
 except (UnicodeError,ValueError): return s

def norm(s):
 return ''.join(c for c in unicodedata.normalize('NFD',repair(s).lower()) if c.isalnum())
def line(s): return s.split()[-1].lstrip('0')
def utm(x,y):
 # Inverse WGS84 UTM 14N, EPSG:32614 (USGS Snyder series).
 a=6378137.;e=.0066943799901413165;k=.9996;e1=(1-math.sqrt(1-e))/(1+math.sqrt(1-e));mu=y/k/(a*(1-e/4-3*e*e/64-5*e**3/256))
 fp=mu+(3*e1/2-27*e1**3/32)*math.sin(2*mu)+(21*e1**2/16-55*e1**4/32)*math.sin(4*mu)+151*e1**3/96*math.sin(6*mu)+1097*e1**4/512*math.sin(8*mu)
 ep=e/(1-e);c=ep*math.cos(fp)**2;t=math.tan(fp)**2;n=a/math.sqrt(1-e*math.sin(fp)**2);r=a*(1-e)/(1-e*math.sin(fp)**2)**1.5;d=(x-500000)/(n*k)
 lat=fp-n*math.tan(fp)/r*(d*d/2-(5+3*t+10*c-4*c*c-9*ep)*d**4/24+(61+90*t+298*c+45*t*t-252*ep-3*c*c)*d**6/720)
 lon=(d-(1+2*t+c)*d**3/6+(5-2*c+28*t-3*c*c+8*ep+24*t*t)*d**5/120)/math.cos(fp)
 return [round(-99+math.degrees(lon),7),round(math.degrees(lat),7)]
def shapes(z,n):
 b=z.read(n);pos=100;out=[]
 while pos<len(b):
  size=struct.unpack_from('>i',b,pos+4)[0]*2;raw=b[pos+8:pos+8+size];pos+=8+size;t=struct.unpack_from('<i',raw)[0]
  if t in (1,11):out.append({'type':'Point','coordinates':list(struct.unpack_from('<dd',raw,4))})
  elif t in (3,5,13,15):
   np,nn=struct.unpack_from('<ii',raw,36);parts=list(struct.unpack_from('<'+'i'*np,raw,44))+[nn];xy=[list(struct.unpack_from('<dd',raw,44+4*np+i*16)) for i in range(nn)];coords=[xy[parts[i]:parts[i+1]] for i in range(np)];out.append({'type':'MultiLineString' if t in (3,13) else 'Polygon','coordinates':coords})
  else: raise ValueError(t)
 return out
z=zipfile.ZipFile(INPUT/'stc_metro.zip');features=[]
for kind in ['estaciones','lineas']:
 n=next(n[:-4] for n in z.namelist() if kind in n and n.endswith('.shp'));rows=dbf(z,n+'.dbf');geoms=shapes(z,n+'.shp')
 for p,g in zip(rows,geoms):
  if kind=='lineas':g['coordinates']=[[utm(*xy) for xy in part] for part in g['coordinates']]
  else: assert -100<g['coordinates'][0]<-98 # point PRJ is geographic despite filename
  features.append({'type':'Feature','properties':{'line':line(p['LINEA']),'name':p.get('NOMBRE',p.get('RUTA')),'id':p.get('CVE_EST',p['LINEA']),'kind':kind},'geometry':g})
stations=[f for f in features if f['properties']['kind']=='estaciones'];lookup={(f['properties']['line'],norm(f['properties']['name'])):i for i,f in enumerate(stations)}
# Explicit renamed station crosswalk, never fuzzy joins.
alias={'balderas':'balderas','guerrero':'guerrero','etiopia/plazadelatransparencia':'etiopia','etiopiaplazadelatransparencia':'etiopia','uam1':'uami','uam i':'uami','zocalotenochititlan':'zocalo','zocalotenochtitlan':'zocalo','ferreriaalamex':'ferreria','ferreriaarenaciudaddemexico':'ferreria','tecnologico':'tecnologico'}
days={};unmatched=collections.Counter();total=0;records=0
with open(INPUT/'afluenciastc_desglosado_09_2026.csv',encoding='utf-8-sig') as file:
 for r in csv.DictReader(file):
  records+=1;d=r['fecha'];l=line(repair(r['linea']));name=norm(r['estacion']);v=int(r['afluencia']);total+=v
  key=(l,name);i=lookup.get(key)
  if i is None:i=lookup.get((l,{'mixiuhca':'mixhiuca','ninosheroes':'ninosheroespoderjudicialcdmx',**alias}.get(name,name)))
  if i is None: unmatched[(l,repair(r['estacion']))]+=v;continue
  if d not in days:days[d]=[0]*len(stations)
  days[d][i]+=v
print('UNMATCHED',unmatched)
if unmatched:raise SystemExit('Add audited aliases before continuing')
dates=sorted(days);latest=dates[-1];series=[days[d] for d in dates];assert sum(map(sum,series))==total
colors={'1':'#ec008c','2':'#005eb8','3':'#a7a500','4':'#6bc5b1','5':'#ffd100','6':'#ed1c24','7':'#f36e21','8':'#008c45','9':'#512f2e','A':'#981d97','B':'#a6a8ab','12':'#b9975b'}
obj={'dates':dates,'values':series,'stations':stations,'lines':[f for f in features if f['properties']['kind']=='lineas'],'colors':colors,'meta':{'records':records,'source_total':total,'start':dates[0],'end':latest,'station_line_count':len(stations),'join':'195 station-line pairs; explicit renamed-station crosswalk; payment types summed','csv_sha256':hashlib.sha256((INPUT/'afluenciastc_desglosado_09_2026.csv').read_bytes()).hexdigest()}}
(OUT/'metro.json').write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')))
(OUT/'red.geojson').write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False))
(OUT/'validacion.json').write_text(json.dumps({'dates':len(dates),'records':records,'total':total,'unmatched':0,'latest':latest,'latest_total':sum(days[latest]),'station_line_count':len(stations)},indent=2))
print((OUT/'validacion.json').read_text())
