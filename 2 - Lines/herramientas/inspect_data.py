import zipfile,struct,csv,collections,json

def dbf(z,n):
 b=z.read(n); count=struct.unpack_from('<I',b,4)[0]; head,rec=struct.unpack_from('<HH',b,8); fields=[];p=32
 while b[p]!=13:
  name=b[p:p+11].split(b'\0')[0].decode();typ=chr(b[p+11]);size=b[p+16];fields.append((name,typ,size));p+=32
 out=[]
 for i in range(count):
  raw=b[head+i*rec:head+(i+1)*rec];p=1;row={}
  for name,t,size in fields:
   v=raw[p:p+size].decode('utf-8',errors='replace').strip();p+=size;row[name]=v
  out.append(row)
 return out
if __name__=='__main__':
 for file in ['stc_metro','cetram']:
  z=zipfile.ZipFile('upload/'+file+'.zip')
  for n in z.namelist():
   if n.endswith('.dbf'):
    rows=dbf(z,n);print(n,len(rows),json.dumps(rows[:2],ensure_ascii=False));print('names', [r for r in rows[:20]] if 'lineas' in n else '')
 dates=collections.Counter();lines=collections.Counter();bad=0
 with open('upload/afluenciastc_desglosado_09_2026.csv',encoding='utf-8-sig') as f:
  for r in csv.DictReader(f): dates[r['fecha']]+=1;lines[r['linea']]+=1
 print('DATES',min(dates),max(dates),'LINES',lines,'latest rows',dates[max(dates)])
