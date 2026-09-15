"""按已收录文章 ID 下载官方九语种文章；缓存文件在 resource/gameplay。"""
from pathlib import Path
import json, subprocess, concurrent.futures
from bs4 import BeautifulSoup
root=Path(__file__).resolve().parents[2];out=root/'dist/static/i18n/gameplay';out.mkdir(parents=True,exist_ok=True)
slugs=sorted(json.loads((out/'zh.json').read_text()))
langs=['zh','en','ja','ko','fr','de','es','pt','ru']
def fetch(job):
 lang,slug=job;locale='zh-Hans' if lang=='zh' else lang
 url=f'https://support.playoxide.com/hc/{locale}/oxide/articles/{slug}'
 p=root/'resource/gameplay'/lang/(slug+'.html');p.parent.mkdir(parents=True,exist_ok=True)
 if not p.exists():
  tmp=p.with_suffix('.part')
  subprocess.run(['curl','-fsSL','--retry','2','--retry-all-errors','--connect-timeout','15','--max-time','60',url,'-o',str(tmp)],check=True,stderr=subprocess.PIPE)
  tmp.rename(p)
 soup=BeautifulSoup(p.read_text(),'html.parser');body=soup.select_one('.tiptap-container, .mdx-container');title=soup.find('h1')
 assert body and title and soup.html.get('lang')==locale,(lang,slug,'missing article')
 # 仅保留文章结构和公开媒体，不导入客服站脚本、样式及表单。
 allowed={'p','br','strong','em','u','s','ul','ol','li','h2','h3','h4','blockquote','a','img','table','thead','tbody','tr','th','td','hr','div','aside','span'}
 for el in list(body.find_all(True)):
  if el.name is None or el.parent is None:continue
  if el.name in {'script','style','svg','form','input','button'}:el.decompose();continue
  if el.name not in allowed:el.unwrap();continue
  el.attrs={k:v for k,v in el.attrs.items() if k in {'href','src','alt','title','colspan','rowspan'}}
  for k in ['href','src']:
   if k in el.attrs:
    from urllib.parse import urljoin,urlparse
    val=urljoin(url,el[k]);el[k]=val
    if urlparse(val).scheme not in {'http','https'}:del el[k]
 text=body.get_text(' ',strip=True)
 assert len(text)>30,(lang,slug,'empty article')
 return lang,slug,{'title':title.get_text(' ',strip=True),'html':body.decode_contents(),'text':text,'source_url':url,'source_locale':locale}
results={l:{} for l in langs};errors=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 fs={pool.submit(fetch,(l,s)):(l,s) for l in langs for s in slugs}
 for n,f in enumerate(concurrent.futures.as_completed(fs),1):
  try:
   lang,slug,row=f.result();results[lang][slug]=row
  except Exception as e:errors.append([fs[f],str(e)]);print('ERROR',fs[f],str(e),flush=True)
  if n%21==0:print('articles',n,'/',len(fs),flush=True)
assert not errors, errors
for lang,rows in results.items():(out/(lang+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
print('DONE',{l:len(r) for l,r in results.items()},'errors',errors,flush=True)
assert not errors
