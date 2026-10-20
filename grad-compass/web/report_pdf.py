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
RENDERER='country-reader-6'


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
    from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Image,LongTable,Table,TableStyle,PageBreak,Flowable,CondPageBreak
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.colors import HexColor
    from PIL import Image as Raster,ImageOps
    s=styles();meta=report['metadata'];doc=meta['canonical_document'];editorial=report.get('reader')
    tree=editorial['content'] if editorial else report['content'];review=meta.get('canonical_factual_review',{'state':'pending'})
    body=[];width=A4[0]-96
    concise=bool(editorial) or any(section['id']=='at-a-glance' for section in tree['sections'])
    if editorial:sections=[section for section in tree['sections'] if section['id'] not in ('introduction','source-guide','evidence-map-binding')]
    else:sections=[section for section in tree['sections'] if section['id']=='at-a-glance' or section['id'].startswith('costs') or section['id'].startswith('timing')] if concise else tree['sections']
    def p(text,style='body'):return Paragraph(text,s[style])
    class Flag(Flowable):
        def __init__(self):super().__init__();self.width=24;self.height=16
        def draw(self):
            for i,color in enumerate(('#171717','#f6ca35','#eb3c45')):self.canv.setFillColor(HexColor(color));self.canv.rect(i*8,0,8,16,fill=1,stroke=0)
    brand=p('GRAD COMPASS · COUNTRY REPORT · READER EDITION','small')
    if meta['country_code']=='BEL':
        branding=Table([[Flag(),brand]],colWidths=[36,width-36]);branding.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),8)]));body.append(branding)
    else:body.append(brand)
    facts=[p(escape(tree['title']),'title'),p('Canonical report v'+str(doc['revision_number'])+' · '+escape(meta.get('report_date') or report['content']['report_date'] or 'Date unknown'),'small'),
        p('Canonical factual review: <b>'+escape(review.get('state','pending'))+'</b> · '+escape(review.get('reviewed_at') or review.get('time') or 'Review date not supplied'),'small')]
    if editorial:
        er=editorial['metadata']['factual_review'];facts.append(p('Reader edition r'+str(editorial['metadata']['revision_number'])+' · Factual review: <b>'+escape(er['state'])+'</b> · Human approval: '+escape(editorial['metadata']['human_approval']['state']),'small'))
    else:facts.append(p('Human approval: '+escape(meta.get('human_approval',{}).get('state','unknown')),'small'))
    labels=' · '.join(label['text'] for label in report['content'].get('labels',[]))
    facts.append(p('Evidence observed: '+escape(meta.get('source_artifact',{}).get('observed_on','date not supplied'))+'. '+escape(labels or 'Observation dates and applicable academic years are distinct.')+' Bounded country conditions; university discovery is separate.','small'))
    asset=_asset() if meta['country_code']=='BEL' else {}
    if asset:
        # A portrait inset preserves the spire and square; the old panoramic crop
        # cut through the subject. The source asset stays byte-for-byte intact.
        with Raster.open(_path(asset)) as image:
            image=ImageOps.fit(image,(672,756),centering=(.5,.45));raster=io.BytesIO();image.save(raster,format='JPEG');raster.seek(0)
        visual=[Image(raster,width=112,height=126),p(escape(asset['credit'])+' · '+escape(asset['license'])+'<br/><a href="'+escape(asset['source_url'])+'">Photo source</a>','small')]
        cover=Table([[facts,visual]],colWidths=[width-132,132]);cover.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(0,0),(0,0),16),('LEFTPADDING',(1,0),(1,0),12),('RIGHTPADDING',(1,0),(1,0),0),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),6)]));body.append(cover)
    else:body.extend(facts)
    body.append(p('A concise rendition of the selected canonical research. The detailed Markdown contains the complete research, dated public evidence, qualifications, calculations and open questions.','small'))
    if not concise:body.append(PageBreak())
    used_refs=set()
    def linked(block):
        def replace(match):
            return re.sub(r'E\d{2}',lambda m:'<link href="#'+m[0]+'" color="#08647c">'+m[0]+'</link>' if m[0] in tree['sources'] else m[0],match[0])
        return re.sub(r'\[(E\d{2}[^\]]*)\]',replace,block['pdf'])
    for section in sections:
        section_heading=p(escape(section['title']),'heading');body.append(section_heading)
        for item in section['items']:
            if not editorial and concise and section['id'].startswith('timing') and item.get('number',0)>3:continue
            blocks=[b for row in item['rows'] for b in row] if item['type']=='table' else [item['block']]
            used_refs.update(ref for block in blocks for ref in block['refs'])
            if item['type']=='table':
                rows=[[p(linked(block),'header' if i==0 else 'cell') for block in row] for i,row in enumerate(item['rows'])]
                n=len(rows[0]);fractions=[.23,.39,.38] if n==3 else [.38,.62] if n==2 else [1/n]*n
                table=LongTable(rows,colWidths=[width*f for f in fractions],repeatRows=1,hAlign='LEFT',splitByRow=1)
                table_style=TableStyle([('BACKGROUND',(0,0),(-1,0),HexColor('#153b4d')),('ROWBACKGROUNDS',(0,1),(-1,-1),[HexColor('#f0f7f8'),HexColor('#ffffff')]),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),8),('LINEBELOW',(0,0),(-1,-1),.4,HexColor('#cadde3'))]);table.setStyle(table_style)
                if item is section['items'][0]:
                    # Keep a heading with enough of its table, without forcing the
                    # entire table onto a fresh page and wasting the cover tail.
                    body.pop();section_heading.keepWithNext=False
                    first_rows=Table(rows[:2],colWidths=[width*f for f in fractions]);first_rows.setStyle(table_style)
                    minimum=first_rows.wrap(width,10000)[1]+section_heading.wrap(width,10000)[1]+section_heading.getSpaceBefore()+section_heading.getSpaceAfter()
                    body.extend([CondPageBreak(minimum),section_heading,table])
                else:body.append(table)
                body.append(Spacer(1,10))
            else:
                block=item['block'];prefix=(str(item['number'])+'. ' if item.get('number') else '• ') if item['type']=='list_item' else ''
                body.append(p(prefix+linked(block)))
    body.append(p('Sources','heading'))
    body.append(p('E references are editorial topic mappings, not audited claim-level citations. Full URLs, passage locators, observation dates and evidence qualifications are in the detailed Markdown.','small'))
    source_cells=[]
    for ref,source in tree['sources'].items():
        if concise and ref not in used_refs:continue
        heading=p('<a name="'+ref+'"/>'+ref+' · '+escape(source['topic'].split(' — ')[0]),'source_title')
        links=['<a href="'+escape(link['url'],{'"':'&quot;'})+'" color="#08647c">'+escape(link['label'])+'</a>' for link in source['links']]
        source_cells.append([heading,p(' · '.join(links) if links else 'Editorial synthesis; see the detailed evidence map.','small')])
    source_rows=[source_cells[i:i+2]+([[]] if len(source_cells[i:i+2])==1 else []) for i in range(0,len(source_cells),2)]
    if source_rows:
        grid=Table(source_rows,colWidths=[width/2,width/2],hAlign='LEFT');grid.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),12),('TOPPADDING',(0,0),(-1,-1),0),('BOTTOMPADDING',(0,0),(-1,-1),3)]));body.append(grid)
    body.append(p('Shared origin: canonical report v'+str(doc['revision_number'])+(' · reader edition r'+str(editorial['metadata']['revision_number']) if editorial else '')+'. The detailed Markdown includes exact version references and full research. Personal annotations are not included.','small'))
    provenance=json.dumps({'canonical_revision_id':doc['revision_id'],'canonical_sha256':doc['sha256'],'reader_document_sha256':editorial['metadata']['sha256'] if editorial else None},sort_keys=True)
    def document(output):return SimpleDocTemplate(output,pagesize=A4,leftMargin=48,rightMargin=48,topMargin=38,bottomMargin=46,title=tree['title'],subject=provenance,author='Grad Compass',pageCompression=1)
    first=document(io.BytesIO());first.build(deepcopy(body));total=first.page
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Compass',7);canvas.setFillColor(HexColor('#466473'));canvas.drawString(48,26,'Grad Compass · '+meta['country_code']+' · canonical report v'+str(report['metadata']['canonical_document']['revision_number'])+' · reader edition');canvas.drawRightString(A4[0]-48,26,str(doc.page)+' / '+str(total));canvas.restoreState()
    output=io.BytesIO();pdf=document(output);pdf.build(body,onFirstPage=footer,onLaterPages=footer);return output.getvalue()


def ensure_pdf(workspace,report,pdf_sha256=None):
    with PDF_LOCK:
        root=private_directory(workspace.directory/'report-cache'/report['key']/report['edition'])
        stem=RENDERER+('-'+report['reader']['id'] if report.get('reader') else '')
        path=regular(root/(stem+'.pdf'))
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
        from web.report_export import filename as export_filename
        source=re.fullmatch(r'country-reader-\d+-([a-f0-9]{64})',path.stem)
        export_report={**report,'reader':None}
        if source:
            from web.report_editions import get as get_edition
            export_report['reader']=get_edition(workspace,report,source[1])
        filename=export_filename(export_report,('-reader' if path.stem.startswith('country-reader-') else '')+'.pdf')
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
