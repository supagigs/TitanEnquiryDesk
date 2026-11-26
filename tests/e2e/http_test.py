import requests,sys
B='http://127.0.0.1:8000';H={'Host':'titan-staging.localhost'}
def login(u,p):
    s=requests.Session();s.headers.update(H);r=s.post(B+'/api/method/login',data={'usr':u,'pwd':p});assert r.ok,r.text;return s
res=[]
def check(name,cond):res.append((name,bool(cond)));print(('PASS' if cond else 'FAIL'),name)
g=requests.get(B+'/titan-desk',headers=H,allow_redirects=False);check('guest redirected to login',g.status_code in (301,302,303) and 'login' in g.headers.get('Location',''))
m=login('mirza@titan.test','Titan@12345')
r=m.post(B+'/api/method/titan_desk.demo.seed_demo');check('manager seeds demo data',r.ok)
p=m.get(B+'/titan-desk');check('desk page loads for manager',p.ok and 'csrf_token' in p.text and '/assets/titan_desk/frontend/' in p.text)
a=m.get(B+'/assets/titan_desk/frontend/'+p.text.split('/assets/titan_desk/frontend/')[1].split('"')[0]);check('SPA bundle served',a.ok and len(a.content)>10000)
t=m.get(B+'/api/method/titan_desk.desk.get_today').json()['message'];check('today API returns escalated leads',len(t['needs'])>=1)
inbox=m.get(B+'/api/method/titan_desk.desk.get_inbox',params={'view':'All'}).json()['message'];check('inbox lists 8 demo leads',len(inbox)>=8)
lead=next(l['name'] for l in inbox if l['organization']=='Vardhan Valves')
s=login('sales@titan.test','Titan@12345')
r=s.get(B+'/api/method/titan_desk.desk.get_conversation',params={'lead':lead});check('sales user reads unassigned lead',r.ok)
tok=s.get(B+'/titan-desk').text.split("window.csrf_token = '")[1].split("'")[0]
r=s.post(B+'/api/method/titan_desk.api.take_over',json={'lead':lead});check('take over without CSRF token refused',r.status_code in (400,403))
r=s.post(B+'/api/method/titan_desk.api.take_over',json={'lead':lead},headers={'X-Frappe-CSRF-Token':tok});check('sales user takes over lead',r.ok and r.json()['message']['lead_owner']=='sales@titan.test')
mt=m.get(B+'/titan-desk').text.split("window.csrf_token = '")[1].split("'")[0]
r=m.post(B+'/api/method/titan_desk.desk.send_reply',json={'lead':lead,'text':'Which pressure class do you need?'},headers={'X-Frappe-CSRF-Token':mt});check('manager replies on WhatsApp (simulated, within 24h)',r.ok)
other=next(l['name'] for l in inbox if l['organization']=='Gearline Industries')
r=s.post(B+'/api/method/titan_desk.api.assign',json={'lead':other,'user':'mirza@titan.test'},headers={'X-Frappe-CSRF-Token':tok});check('sales user cannot assign to someone else',r.status_code==403)
g=requests.post(B+'/api/method/titan_desk.desk.get_today',headers=H);check('guest API refused',g.status_code==403)
print(f"{sum(c for _,c in res)}/{len(res)} passed");sys.exit(0 if all(c for _,c in res) else 1)
