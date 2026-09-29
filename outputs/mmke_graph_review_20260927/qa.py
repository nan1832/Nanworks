"""Read-only source verification and browser interaction/layout checks."""
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(OUT.parent / 'mmke_graph_quality_audit_20260926' / 'preview_tools'))
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch(executable_path=r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe', headless=True)
    context = browser.new_context(viewport={'width': 1600, 'height': 1080}, accept_downloads=True)
    page = context.new_page()
    errors, external = [], []
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.on('request', lambda req: external.append(req.url) if req.url.startswith(('http:', 'https:')) else None)
    page.goto((OUT / 'index.html').as_uri(), wait_until='load', timeout=120000)
    page.wait_for_function('window.REVIEW_APP && document.querySelectorAll(".node").length > 0')
    assert page.locator('#entity-name').inner_text() == "Scott's oriole"
    assert page.locator('#samples .sample').count() == 955
    assert page.evaluate('JSON.parse(document.querySelector("#source-content pre").textContent).alt === REVIEW_DATA.datasets.eval[10].record.alt')
    assert page.locator('.edge-path').count() == 9
    page.locator('.node').first.press('Enter')
    assert "Scott's oriole" in page.locator('#detail-content').inner_text()
    page.locator('.edge-hit').first.press('Enter')
    assert 'runtime_edge' in page.locator('#detail-content').inner_text()
    page.locator('[data-tab=compare]').click()
    assert 'John Gould' in page.locator('#source-content').inner_text()
    page.screenshot(path=str(OUT / 'preview-desktop.png'), full_page=True)
    page.locator('#group').select_option('G3_EditOnly0hop')
    assert page.locator('.edge-path').count() == 5
    page.locator('#group').select_option('G3_Overlay1hop')
    for variant in ['G3_RealOnly', 'G4_RandomMatched', 'G3_Overlay1hop']:
        page.locator('#group').select_option(variant)
        assert page.locator('.edge-path').count() == page.evaluate('(g)=>REVIEW_DATA.datasets.eval[10].graphs[g].raw.semantic_edge_count', variant)
    page.locator('#show-excluded').check()
    assert page.locator('.edge-label.excluded').count() == page.evaluate('REVIEW_DATA.datasets.eval[10].excluded.length')
    page.locator('#show-loops').check()
    assert page.locator('.edge-path').count() == page.evaluate('REVIEW_DATA.datasets.eval[10].graphs.G3_Overlay1hop.raw.edge_src.length + REVIEW_DATA.datasets.eval[10].excluded.length')
    page.locator('#show-loops').uncheck()
    page.locator('#show-excluded').uncheck()
    before = page.evaluate('REVIEW_APP.graph.nodes[0].x')
    box = page.locator('.node').first.bounding_box()
    page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
    page.mouse.down()
    page.mouse.move(box['x'] + box['width']/2 + 50, box['y'] + box['height']/2 + 20, steps=5)
    page.mouse.up()
    assert abs(page.evaluate('REVIEW_APP.graph.nodes[0].x') - before) > 10
    scale = page.evaluate('REVIEW_APP.graph.k')
    page.locator('#zoom-in').click()
    assert page.evaluate('REVIEW_APP.graph.k') > scale
    page.locator('#fit').click()
    page.locator('#search').fill('#14')
    assert page.locator('#samples .sample').count() == 1
    page.locator('#samples .sample').click()
    assert page.locator('.node').count() == 1
    assert page.locator('.edge-path').count() == 0
    assert not page.locator('#graph-warning').is_hidden()
    page.locator('#show-excluded').check()
    assert page.locator('.node').count() == 5
    assert page.locator('.edge-path').count() == 4
    page.screenshot(path=str(OUT / 'preview-excluded.png'), full_page=True)
    page.locator('#verdict').select_option('issue')
    page.locator('#note').fill('QA临时意见：四条事实被过滤。')
    page.reload(wait_until='load')
    assert page.locator('#note').input_value() == 'QA临时意见：四条事实被过滤。'
    with page.expect_download() as download:
        page.locator('#export-reviews').click()
    file = Path(download.value.path())
    payload = json.loads(file.read_text(encoding='utf-8'))
    assert len(payload['annotations']) == 1
    # Exercise real import validation with the exported bytes; existing values are retained.
    page.locator('#review-file').set_input_files({'name':'reviews.json','mimeType':'application/json','buffer':file.read_bytes()})
    page.wait_for_function('document.querySelector("#toast").textContent.includes("保留原值")')
    page.locator('#review-file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"version":"wrong","annotations":{}}'})
    page.wait_for_function('document.querySelector("#toast").textContent.includes("导入失败")')
    page.locator('#split').select_option('train')
    assert page.locator('#samples .sample').count() == 636
    largest = page.evaluate('REVIEW_DATA.datasets.train.reduce((a,b)=>a.graphs.G3_Overlay1hop.raw.node_ids.length>b.graphs.G3_Overlay1hop.raw.node_ids.length?a:b).index')
    page.evaluate('(i)=>REVIEW_APP.select("train",i)', largest)
    assert page.locator('.node').count() == 678
    assert page.locator('.edge-path').count() == 724
    assert '大图' in page.locator('#graph-warning').inner_text()
    page.screenshot(path=str(OUT / 'preview-large-graph.png'), full_page=True)
    page.evaluate('REVIEW_APP.select("eval",10)')
    page.locator('#search').fill('no-such-entity-xyz')
    assert page.locator('#samples .sample').count() == 0
    assert '没有匹配' in page.locator('#samples').inner_text()
    page.locator('#search').fill('')
    page.locator('#filter').select_option('neighbors')
    assert page.locator('#samples .sample').count() == 21
    page.locator('#filter').select_option('empty')
    assert page.locator('#samples .sample').count() == 28
    page.locator('#filter').select_option('all')
    page.locator('#direction').select_option('message')
    assert 'edge_src' in page.locator('#graph-counts').inner_text()
    page.locator('[data-tab=image]').click()
    assert page.locator('#source-content img').evaluate('(e)=>e.complete && e.naturalWidth>0')
    page.set_viewport_size({'width':390,'height':900})
    page.wait_for_timeout(300)
    dims = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
    assert dims['scroll'] <= dims['width'] + 1, dims
    page.screenshot(path=str(OUT / 'preview-mobile.png'), full_page=True)
    page.locator('#graph-area').scroll_into_view_if_needed()
    page.screenshot(path=str(OUT / 'preview-mobile-graph.png'))
    assert not errors, errors
    assert not external, external
    # Test profile is ephemeral; QA annotations do not enter the user's browser.
    result={'pass':True,'samples':{'eval':955,'train':636},'max_graph':{'index':largest,'nodes':678,'edges':724},'mobile':dims,'javascript_errors':errors,'external_requests':external,'checks':['original JSON values','4 graph variants available','node/edge evidence','group switch','excluded overlay','self loops','drag/zoom','empty graph','search/filter','local review persistence','export/import validation','large graph no truncation','direction switch','sample image','mobile overflow']}
    (OUT / 'browser-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False))
    browser.close()
