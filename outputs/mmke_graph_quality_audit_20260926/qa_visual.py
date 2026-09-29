import sys,json
from pathlib import Path
p=Path(__file__).resolve().parent
sys.path.insert(0,str(p/'preview_tools'))
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',headless=True)
    page=browser.new_page(viewport={'width':1100,'height':1000},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda err:errors.append(str(err)))
    page.goto((p/'preview.html').as_uri())
    frame=page.frame_locator('iframe')
    frame.locator('#audit-graph text').first.wait_for()
    assert 'John Gould' in frame.locator('#audit-alt').inner_text()
    checks=[]
    for i,edges in [('10',9),('0',4),('14',0)]:
        frame.locator('#audit-sample').select_option(i)
        assert frame.locator('#audit-edges tr').count()==edges
        assert frame.locator('#audit-scores tr').count()==7
        checks.append({'index':i,'edges':edges})
    frame.locator('#audit-sample').select_option('10')
    frame.locator('#audit-group').select_option('G3_EditOnly0hop')
    assert frame.locator('#audit-edges tr').count()==5
    frame.locator('#audit-group').select_option('G3_Overlay1hop')
    content_height=frame.locator('#mmke-graph-audit').evaluate('(e)=>e.getBoundingClientRect().height')
    page.locator('iframe').evaluate('(e,h)=>e.style.height=(h+40)+"px"',content_height)
    page.screenshot(path=str(p/'preview-desktop.png'),full_page=True)
    frame.locator('#audit-scores').scroll_into_view_if_needed()
    page.screenshot(path=str(p/'preview-details.png'))
    page.set_viewport_size({'width':390,'height':900})
    page.wait_for_timeout(400)
    width=frame.locator('#mmke-graph-audit').evaluate('(e)=>({w:e.clientWidth,sw:e.scrollWidth,svg:e.querySelector("svg").getBoundingClientRect().width})')
    assert width['sw']<=width['w']+2,width
    content_height=frame.locator('#mmke-graph-audit').evaluate('(e)=>e.getBoundingClientRect().height')
    page.locator('iframe').evaluate('(e,h)=>e.style.height=(h+40)+"px"',content_height)
    page.screenshot(path=str(p/'preview-mobile.png'),full_page=True)
    frame.locator('#audit-graph').scroll_into_view_if_needed()
    page.screenshot(path=str(p/'preview-mobile-graph.png'))
    assert not errors,errors
    (p/'visual_qa.json').write_text(json.dumps({'interactions':checks,'zero_hop_edges':5,'mobile':width,'javascript_errors':errors},indent=2),encoding='utf8')
    print('PASS',checks,width)
    browser.close()
