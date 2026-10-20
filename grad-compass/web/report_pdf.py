"""Offline PDF export and page/text geometry from the same canonical content tree."""
import hashlib
import io
import json
from pathlib import Path
import re
import threading
from copy import deepcopy
from xml.sax.saxutils import escape

from web.local import private_directory,regular
from web.report_packages import immutable

PDF_LOCK=threading.RLock()
ASSETS=Path(__file__).parent/'assets'
RENDERER='country-reader-2'


def styles():
    import reportlab
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.styles import ParagraphStyle
    root=Path(reportlab.__file__).parent/'fonts'
    for name,file in [('Compass','Vera.ttf'),('Compass-Bold','VeraBd.ttf'),('Compass-Italic','VeraIt.ttf'),('Compass-BoldItalic','VeraBI.ttf')]:
        if name not in pdfmetrics.getRegisteredFontNames():pdfmetrics.registerFont(TTFont(name,str(root/file)))
    pdfmetrics.registerFontFamily('Compass',normal='Compass',bold='Compass-Bold',italic='Compass-Italic',boldItalic='Compass-BoldItalic')
    base=ParagraphStyle('body',fontName='Compass',fontSize=9.5,leading=15,textColor='#193c4e',spaceAfter=10,allowWidows=0,allowOrphans=0)
    return {'body':base,'title':ParagraphStyle('title',parent=base,fontName='Compass-Bold',fontSize=24,leading=30,spaceAfter=18),
            'heading':ParagraphStyle('heading',parent=base,fontName='Compass-Bold',fontSize=16,leading=21,spaceBefore=20,spaceAfter=12,keepWithNext=True),
            'small':ParagraphStyle('small',parent=base,fontSize=8,leading=12,spaceAfter=7),
            'cell':ParagraphStyle('cell',parent=base,fontSize=8,leading=12,spaceAfter=3),
            'header':ParagraphStyle('header',parent=base,fontName='Compass-Bold',fontSize=8,leading=12,textColor='#ffffff'),
            'source_title':ParagraphStyle('source_title',parent=base,fontName='Compass-Bold',fontSize=9,leading=13,spaceBefore=10,spaceAfter=4,keepWithNext=True)}


def _asset():
    manifest=json.loads((ASSETS/'countries.json').read_text())
    return manifest.get('BEL',{})


def _path(asset):
    path=ASSETS/Path(asset['path']).name
    if hashlib.sha256(path.read_bytes()).hexdigest()!=asset['sha256']:raise ValueError('Report visual asset hash mismatch')
    return path


def build(report):
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,LongTable,TableStyle,PageBreak,KeepTogether,Flowable
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from PIL import Image as Raster
    s=styles();meta=report['metadata'];doc=meta['canonical_document'];tree=report['content'];review=meta.get('canonical_factual_review',{'state':'pending'})
    body=[];width=A4[0]-96
    # Until a producer editorial edition is agreed/delivered, select complete
    # canonical passages. Never synthesize a shorter factual assertion.
    concise=any(section['id']=='at-a-glance' for section in tree['sections'])
    sections=[section for section in tree['sections'] if section['id']=='at-a-glance' or section['id'].startswith('costs') or section['id'].startswith('timing')] if concise else tree['sections']
    def p(text,style='body'):return Paragraph(text,s[style])
    body.append(p('GRAD COMPASS · COUNTRY REPORT · READER EDITION','small'))
    if meta['country_code']=='BEL':
        class Flag(Flowable):
            width=30;height=20
            def draw(self):
                for i,color in enumerate(('#171717','#f6ca35','#eb3c45')):self.canv.setFillColor(HexColor(color));self.canv.rect(i*10,0,10,20,fill=1,stroke=0)
        body.extend([Flag(),Spacer(1,3 if concise else 10)])
    body.append(p(escape(tree['title']),'title'))
    asset=_asset() if meta['country_code']=='BEL' else {}
    if asset:
        with Raster.open(_path(asset)) as image:
            # Screen and print share the same photograph; crop locally, never rewrite it.
            target_ratio=width/90;crop_height=int(image.width/target_ratio);top=max(0,int(image.height*.52-crop_height/2));image=image.crop((0,top,image.width,min(image.height,top+crop_height)));image.load();raster=io.BytesIO();image.save(raster,format='JPEG');raster.seek(0)
        body.append(Image(raster,width=width,height=90))
        body.append(p(escape(asset['credit'])+' · '+escape(asset['license'])+' · <a href="'+escape(asset['source_url'])+'">Image source</a>','small'))
    body.extend([p('Report v'+str(doc['revision_number'])+' · '+escape(meta.get('report_date') or tree['report_date'] or 'Date not separately supplied'),'small'),
                 p('Factual review: <b>'+escape(review.get('state','pending'))+'</b> · Review date: '+escape(review.get('reviewed_at',review.get('time','Not supplied')))+' · Human approval: '+escape(meta.get('human_approval',{}).get('state','unknown')),'small'),
                 p('Evidence observed: '+escape(meta.get('source_artifact',{}).get('observed_on','Not separately supplied'))+' · Target-year terms are not inferred from historical figures. Bounded country report; university discovery is separate.','small')])
    if concise:body.append(p('<b>'+' · '.join(escape(label['text']) for label in tree.get('labels',[]))+'</b>','small'))
    else:
        for label in tree.get('labels',[]):body.append(p('<b>'+escape(label['text'])+'</b>','small'))
    if asset.get('locator') and not concise:
        locator=asset['locator'];body.append(Image(str(_path(locator)),width=230,height=138));body.append(p(escape(locator['caption'])+' · '+escape(locator['credit'])+' · '+escape(locator['license']),'small'))
    body.append(p('Reader edition: selected complete passages from canonical report v'+str(doc['revision_number'])+'. The companion detailed Markdown includes all study routes, funding conditions, residence rules, calculations, source observations and the complete evidence map. This extract is not a replacement factual review.','small'))
    if not concise:body.append(PageBreak())
    def sources(block):
        refs=[r for r in block['refs'] if r in tree['sources']]
        return p('Evidence: '+', '.join('<link href="#'+r+'" color="#08647c">'+r+'</link>' for r in refs),'small') if refs else None
    used_refs=set()
    for section in sections:
        body.append(p(escape(section['title']),'heading'))
        if 'funding' in section['id'] or 'costs' in section['id']:body.append(p('<b>Figures retain their stated year, region and unit. Target-year terms remain unconfirmed; competitive awards are conditional.</b>','small'))
        for item in section['items']:
            if concise and section['id'].startswith('timing') and item.get('number',0)>3:continue
            blocks=[b for row in item['rows'] for b in row] if item['type']=='table' else [item['block']]
            used_refs.update(ref for block in blocks for ref in block['refs'])
            if item['type']=='table':
                rows=[]
                for i,row in enumerate(item['rows']):
                    rows.append([p(block['pdf']+(' <font size="7">'+', '.join('<link href="#'+r+'" color="#08647c">'+r+'</link>' for r in block['refs'] if r in tree['sources'])+'</font>' if block['refs'] else ''),'header' if i==0 else 'cell') for block in row])
                n=len(rows[0]);fractions=[.21,.40,.39] if n==3 else [1/n]*n
                table=LongTable(rows,colWidths=[width*f for f in fractions],repeatRows=1,hAlign='LEFT',splitByRow=1)
                table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#153b4d')),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#f0f7f8'),HexColor('#ffffff')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),9),('RIGHTPADDING',(0,0),(-1,-1),9),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LINEBELOW',(0,0),(-1,-1),.4,HexColor('#cadde3'))]))
                body.extend([table,Spacer(1,12)])
            else:
                block=item['block'];prefix=(str(item['number'])+'. ' if item.get('number') else '• ') if item['type']=='list_item' else ''
                citation=sources(block)
                paragraph=p(prefix+block['pdf']);paragraph.keepWithNext=bool(citation);body.append(paragraph)
                if citation:body.append(citation)
    body.append(p('Sources and detailed companion','heading'))
    body.append(p('Editorial topic mappings, not newly verified claim-level citations. Full evidence-map text and dated finding-level records are included in Download detailed Markdown in the app. This reader edition preserves the selected canonical wording; omitted detail remains in that companion.','small'))
    for ref,source in tree['sources'].items():
        if concise and ref not in used_refs:continue
        topic=source['topic'].split(' — ')[0] if concise else source['topic']
        body.append(p('<a name="'+ref+'"/>'+ref+' · '+escape(topic),'source_title' if concise else 'heading'))
        if not concise:body.append(p(escape(source['text']),'small'))
        links=['<a href="'+escape(link['url'],{'"':'&quot;'})+'" color="#08647c">'+escape(link['label'])+'</a>' for link in source['links']]
        if links:body.append(p(' · '.join(links),'small'))
        elif concise:body.append(p('Editorial synthesis; full mapping is included in detailed Markdown.','small'))
    body.append(p('Exact canonical revision and provenance','heading'))
    body.append(p(escape(doc['revision_id'])+'<br/>SHA-256 '+doc['sha256']+'<br/>Reader layout: '+RENDERER+'. Canonical report version is independent of the research result revision. Personal annotations are kept separately.','small'))
    def document(output):return SimpleDocTemplate(output,pagesize=A4,leftMargin=48,rightMargin=48,topMargin=44,bottomMargin=48,title=tree['title'],author='Grad Compass',pageCompression=1)
    # Two ordinary layout passes keep PDF bookmark destinations intact. Saving and
    # replaying canvas states for page totals breaks internal source destinations.
    first=document(io.BytesIO());first.build(deepcopy(body));total=first.page
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Compass',7);canvas.setFillColor(HexColor('#466473'));canvas.drawString(48,28,'Grad Compass · '+meta['country_code']+' · canonical report v'+str(report['metadata']['canonical_document']['revision_number'])+' · reader edition');canvas.drawRightString(A4[0]-48,28,str(doc.page)+' / '+str(total));canvas.restoreState()
    output=io.BytesIO();pdf=document(output);pdf.build(body,onFirstPage=footer,onLaterPages=footer);return output.getvalue()


def ensure_pdf(workspace,report,pdf_sha256=None):
    with PDF_LOCK:
        root=private_directory(workspace.directory/'report-cache'/report['key']/report['edition'])
        path=regular(root/(RENDERER+'.pdf'))
        if pdf_sha256 is not None:
            if not re.fullmatch('[a-f0-9]{64}',pdf_sha256):raise ValueError('Choose the exact saved PDF')
            path=next((p for p in root.glob('*.pdf') if hashlib.sha256(regular(p).read_bytes()).hexdigest()==pdf_sha256),None)
            if path is None:raise ValueError('The exact saved PDF is unavailable in this report edition')
        elif not path.exists():immutable(path,build(report))
        raw=path.read_bytes();meta=report['metadata'];doc=meta['canonical_document']
        manifest=path.with_suffix('.manifest.json')
        expected={'canonical_revision_id':doc['revision_id'],'canonical_sha256':doc['sha256'],'metadata_sha256':report['edition'],'pdf_sha256':hashlib.sha256(raw).hexdigest(),'renderer':path.stem}
        if manifest.exists():
            if json.loads(regular(manifest).read_bytes())!=expected:raise ValueError('Saved PDF no longer matches its canonical export inventory')
        else:immutable(manifest,(json.dumps(expected,sort_keys=True)+'\n').encode())
        # Date is parsed from canonical content if metadata does not separately supply it.
        date=meta.get('report_date')
        if not date:
            match=re.search(r'\*\*Prepared:\*\*\s*(\d{1,2}) (\w+) (\d{4})',report['canonical_bytes'].decode())
            if match:
                from datetime import datetime
                date=datetime.strptime(' '.join(match.groups()),'%d %B %Y').date().isoformat()
        filename=('belgium' if meta['country_code']=='BEL' else meta['country_code'].lower())+'-country-report-'+(date or 'undated')+'-v'+str(doc['revision_number'])+('-reader' if path.stem.startswith('country-reader-') else '')+'.pdf'
        return {'path':path,'sha256':hashlib.sha256(raw).hexdigest(),'filename':filename,'edition':report['edition']}


def page_data(workspace,report,page,image=False,pdf_sha256=None):
    from PyQt6.QtPdf import QPdfDocument,QPdfLinkModel
    from PyQt6.QtCore import QSize,QBuffer,QIODevice,QModelIndex
    with PDF_LOCK:
        pdf=ensure_pdf(workspace,report,pdf_sha256);document=QPdfDocument(None)
        if document.load(str(pdf['path']))!=QPdfDocument.Error.None_:raise ValueError('Could not open the saved PDF')
        if type(page) is not int or not 0<=page<document.pageCount():raise ValueError('Choose a PDF page in this report')
        size=document.pagePointSize(page)
        if image:
            from PyQt6.QtGui import QImage,QPainter
            bitmap=document.render(page,QSize(round(size.width()*1.6),round(size.height()*1.6)))
            paper=QImage(bitmap.size(),QImage.Format.Format_RGB32);paper.fill(0xffffffff);painter=QPainter(paper);painter.drawImage(0,0,bitmap);painter.end()
            buffer=QBuffer();buffer.open(QIODevice.OpenModeFlag.WriteOnly);paper.save(buffer,'PNG');return bytes(buffer.data())
        text=document.getAllText(page).text();words=[]
        for m in re.finditer(r'\S+',text):
            start=len(text[:m.start()].encode('utf-16-le'))//2;length=len(m.group().encode('utf-16-le'))//2
            selection=document.getSelectionAtIndex(page,start,length)
            for bounds in selection.bounds():
                r=bounds.boundingRect();words.append({'start':m.start(),'end':m.end(),'text':m.group(),'x':r.x(),'y':r.y(),'width':r.width(),'height':r.height()})
        model=QPdfLinkModel(None);model.setDocument(document);model.setPage(page);links=[]
        for row in range(model.rowCount(QModelIndex())):
            index=model.index(row,0);url=model.data(index,QPdfLinkModel.Role.Url.value);r=model.data(index,QPdfLinkModel.Role.Rectangle.value)
            if url and re.match('^https?://',url.toString(),re.I):links.append({'url':url.toString(),'x':r.x(),'y':r.y(),'width':r.width(),'height':r.height()})
            else:
                destination=model.data(index,QPdfLinkModel.Role.Page.value);location=model.data(index,QPdfLinkModel.Role.Location.value)
                if type(destination) is int and 0<=destination<document.pageCount():links.append({'page':destination,'location':[location.x(),location.y()],'x':r.x(),'y':r.y(),'width':r.width(),'height':r.height()})
        return {'text':text,'words':words,'links':links,'page':page,'pages':document.pageCount(),'width':size.width(),'height':size.height(),'pdf_sha256':pdf['sha256'],'filename':pdf['filename'],'edition':report['edition']}
