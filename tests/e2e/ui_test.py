import sys
from playwright.sync_api import sync_playwright
B='http://127.0.0.1:8000';import os
OUT=os.environ.get('OUT','docs/screenshots')
errors=[];res=[]
def check(n,c):res.append(c);print('PASS' if c else 'FAIL',n)
with sync_playwright() as p:
    br=p.chromium.launch(args=['--no-sandbox'])
    for vp,tag in [((1440,900),'desktop'),((390,844),'mobile')]:
        ctx=br.new_context(viewport={'width':vp[0],'height':vp[1]});pg=ctx.new_page()
        pg.on('console',lambda m: m.type=='error' and errors.append(m.text))
        pg.on('pageerror',lambda e: errors.append(str(e)))
        r=ctx.request.post(B+'/api/method/login',form={'usr':'mirza@titan.test','pwd':'Titan@12345'});assert r.ok
        pg.add_init_script("localStorage.setItem('titan.toured','1')") if tag=='mobile' else None
        pg.goto(B+'/titan-desk/today');pg.wait_for_timeout(1500)
        if tag=='desktop':
            check('tour opens on first visit',pg.locator('.tcard').count()==1);pg.screenshot(path=f'{OUT}/01-tour-welcome.png')
            pg.keyboard.press('ArrowRight');pg.wait_for_timeout(600);pg.screenshot(path=f'{OUT}/02-tour-step2.png');pg.keyboard.press('Escape');pg.wait_for_timeout(300)
            check('getting started opens after tour',pg.locator('.gs').count()==1);pg.screenshot(path=f'{OUT}/03-getting-started.png');pg.click('.gs button[aria-label=Close]')
        pg.wait_for_timeout(300)
        if pg.locator('.gs').count(): pg.click('.gs button[aria-label=Close]')
        pg.screenshot(path=f'{OUT}/10-today-{tag}.png',full_page=True)
        check(f'today shows escalations ({tag})',pg.locator('.task').count()>=1)
        pg.goto(B+'/titan-desk/inbox');pg.wait_for_timeout(1800)
        check(f'inbox lists chats ({tag})',pg.locator('.wl').count()>=8)
        pg.screenshot(path='/tmp/dbg.png');pg.locator('.wl',has_text='Vardhan').first.click(timeout=5000);pg.wait_for_timeout(1000)
        check(f'conversation shows messages ({tag})',pg.locator('.wm2').count()>=1)
        if tag=='desktop':
            pg.fill('.wcmp input[aria-label=Message]','Thanks! Which pressure class: 150#, 300# or 600#?');pg.click('.wsend');pg.wait_for_timeout(1200)
            check('reply appears in chat',pg.locator('.wm2.out').count()>=1)
        pg.screenshot(path=f'{OUT}/20-inbox-{tag}.png',full_page=tag=='mobile')
        for path,name in [('pipeline','30-pipeline'),('calendar','40-calendar'),('approvals','50-approvals'),('whatsapp','60-whatsapp'),('settings','70-settings')]:
            pg.goto(f'{B}/titan-desk/{path}');pg.wait_for_timeout(1300);pg.screenshot(path=f'{OUT}/{name}-{tag}.png',full_page=True)
            check(f'{path} renders ({tag})',pg.locator('.err').count()==0 and pg.locator('.wrap').inner_text().strip()!='')
        if tag=='desktop':
            pg.goto(B+'/titan-desk/today');pg.evaluate("document.documentElement.dataset.theme='dark'");pg.wait_for_timeout(500);pg.screenshot(path=f'{OUT}/80-today-dark.png')
            pg.evaluate("document.documentElement.dataset.theme='light'");pg.click('text=Collapse');pg.wait_for_timeout(500);pg.screenshot(path=f'{OUT}/81-collapsed-sidebar.png')
        ctx.close()
    br.close()
errors=[e for e in errors if 'favicon' not in e]
check('no browser console errors',not errors)
for e in errors[:10]:print('  console:',e[:200])
print(f'{sum(res)}/{len(res)} passed');sys.exit(0 if all(res) else 1)
