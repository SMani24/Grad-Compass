"use strict";
/* Canonical content, PDF pages and personal annotations share an exact version. */
(() => {
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const chars=value=>Array.from(value),slice=(value,start,end)=>chars(value).slice(start,end).join('');
  const date=value=>value ? value.slice(0,10) : 'Not supplied';
  async function load(url){const response=await fetch(url,{cache:'no-store'});const value=await response.json();if(!response.ok)throw Error(value.error || 'Could not load the saved report.');return value;}
  async function upgrade(old,ctx,code){
    let target=old;
    try{
      const catalog=await load('/api/reports?request_id='+ctx.current.request.request_id);
      const reports=catalog.reports.filter(r=>r.metadata.country_code===code);
      if(!old.isConnected || !reports.length){if(catalog.errors.length){const warning=el('p','Report package needs attention. The original received findings remain available.','report-package-error');old.prepend(warning);}return;}
      let selected=reports[0],annotations={annotations:[],unreconciled:[]},view='report',page=0,pdf=null,pdfEdition=null,pdfSha=null,pending=null,railOpen=false,checked=new Set(),draft=null,requestSequence=0;
      const article=el('article',undefined,'country-report canonical-report');article.id='country-report';article.dataset.country=code;article.dataset.canonical=selected.key;article.dataset.edition=selected.edition;article.dataset.request=ctx.current.request.request_id;old.replaceWith(article);target=article;
      const status=el('p','','reader-status');status.id='reader-status';status.setAttribute('role','status');status.setAttribute('aria-live','polite');
      const header=el('header',undefined,'canonical-header');
      const toolbar=el('div',undefined,'reader-toolbar');toolbar.setAttribute('aria-label','Country report actions');
      const message=text=>{status.textContent=text;};
      const button=(text,fn,id)=>{const b=el('button',text,'quiet-action');b.type='button';if(id)b.id=id;b.addEventListener('click',async()=>{b.disabled=true;try{await fn();}catch(error){message(error.message);}finally{b.disabled=['reader-highlight','reader-comment'].includes(b.id)?!pending?.quote:false;}});return b;};
      const content=el('div',undefined,'canonical-layout'),reading=el('div',undefined,'canonical-reading'),rail=el('aside',undefined,'annotation-panel');rail.setAttribute('aria-label','Highlights, comments and feedback');rail.hidden=true;
      const assets=await load('/report-assets.json');if(!article.isConnected)return;
      function sourceControls(block,box){
        if(!block.refs.length)return;
        const details=el('details',undefined,'canonical-citations');details.append(el('summary','Evidence '+block.refs.join(', ')));
        details.append(el('p','Editorial topic mapping supplied with this canonical report. The original inbox sources remain finding-level.'));
        for(const ref of block.refs){const source=selected.content.sources[ref];if(!source){details.append(el('p',ref+' · Mapping not supplied'));continue;}
          details.append(el('strong',ref+' · '+source.topic));
          for(const link of source.links){const a=el('a',link.label);a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';details.append(a);}
          if(!source.links.length)details.append(el('p',source.text));
        }box.append(details);
      }
      function blockNode(block,tag='p'){
        const n=el(tag);n.dataset.reportBlock=block.id;
        // HTML is emitted by the app's allowlisted Markdown renderer, never raw producer HTML.
        n.innerHTML=block.html;return n;
      }
      function repaintMarks(){
        for(const mark of reading.querySelectorAll('mark[data-annotation]'))mark.replaceWith(...mark.childNodes);
        reading.normalize();
        if(view==='pdf'){paintPdfHighlights();return;}
        for(const a of annotations.annotations.filter(a=>a.selector.view==='report')){
          const s=a.selector,block=[...reading.querySelectorAll('[data-report-block]')].find(n=>n.dataset.reportBlock===s.block_id);if(!block)continue;
          let offset=0;const walker=document.createTreeWalker(block,NodeFilter.SHOW_TEXT),nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
          for(const node of nodes){const length=chars(node.textContent).length,start=Math.max(0,s.start-offset),end=Math.min(length,s.end-offset);offset+=length;if(end<=start)continue;
            const range=document.createRange();range.setStart(node,chars(node.textContent).slice(0,start).join('').length);range.setEnd(node,chars(node.textContent).slice(0,end).join('').length);
            const mark=el('mark');mark.dataset.annotation=a.id;mark.title=a.comment || 'Saved highlight';mark.addEventListener('click',()=>{railOpen=true;renderRail(a.id);});range.surroundContents(mark);
          }
        }
      }
      function renderHeader(){
        header.replaceChildren();const meta=selected.metadata,doc=meta.canonical_document,asset=assets[code];
        const provenance=ctx.technical('Canonical report, review and export binding',{report:meta.report_id,canonical_revision:doc.revision_id,canonical_sha256:doc.sha256,evidence_map_sha256:meta.evidence_map.sha256,
          review_record:meta.canonical_factual_review?.review_id,review_scope:meta.canonical_factual_review?.scope,pdf:'App-generated from this exact canonical content; personal annotations are separate.'});provenance.id='canonical-provenance';
        const secondary=ctx.section.querySelector('#report-history');if(secondary){const previous=secondary.querySelector('#canonical-provenance');if(previous)previous.replaceWith(provenance);else secondary.append(provenance);}
        const photo=el('figure',undefined,'report-photo');photo.append(el('span',code==='BEL'?'🇧🇪':'🌐','photo-fallback'));
        if(asset){const img=el('img');img.src=asset.path;img.alt=asset.alt;img.addEventListener('error',()=>img.remove());photo.prepend(img);const caption=el('figcaption'),credit=el('a',asset.credit+' · '+asset.license);credit.href=asset.source_url;credit.target='_blank';credit.rel='noopener noreferrer';caption.append(credit);photo.append(caption);}header.append(photo);
        const heading=el('div',undefined,'report-heading');heading.append(el('p','COUNTRY REPORT · VERSION '+doc.revision_number,'eyebrow'));
        const title=el('h1');if(asset?.flag){const flag=el('img');flag.src=asset.flag.path;flag.alt=asset.flag.alt;flag.className='report-flag';title.append(flag);}title.append(document.createTextNode(selected.content.title));heading.append(title);
        const review=meta.canonical_factual_review || {state:'pending'},badges=el('div',undefined,'report-badges');for(const text of ['Factual review: '+review.state,'Human approval: '+(meta.human_approval?.state || 'unknown')])badges.append(el('span',text));heading.append(badges);
        heading.append(el('p','This bounded country report does not establish exhaustive coverage, programme eligibility or completed university discovery.'));
        const facts=el('dl',undefined,'report-facts');for(const [label,value] of [['Report date',selected.content.report_date || meta.report_date || 'Unknown'],['Evidence observed',meta.source_artifact?.observed_on || 'See dated evidence'],['Review date',date(review.reviewed_at || review.time)],['Requested intake',ctx.current.request.preferences.intake || 'Not specified']]){const cell=el('div');cell.append(el('dt',label),el('dd',value));facts.append(cell);}header.append(heading,facts);
        const terms=el('div',undefined,'report-term-labels');for(const label of selected.content.labels || [])terms.append(el('span',label.text,'term-'+label.kind));header.append(terms);
        if(annotations.unreconciled.length){const warning=el('p',annotations.unreconciled.length+' annotations belong to earlier report versions and have not been reconciled. Choose the earlier version to review them.','version-warning');header.append(warning);}
      }
      function renderReport(){
        reading.replaceChildren();const asset=assets[code];
        if(asset?.locator){const figure=el('figure',undefined,'report-locator'),img=el('img');img.src=asset.locator.path;img.alt=asset.locator.alt;img.addEventListener('error',()=>{figure.replaceChildren(el('p','Locator image unavailable. The report remains readable.'));});const credit=el('a',asset.locator.caption+' '+asset.locator.credit+' · '+asset.locator.license);credit.href=asset.locator.source_url;credit.target='_blank';credit.rel='noopener noreferrer';const caption=el('figcaption');caption.append(credit);figure.append(img,caption);reading.append(figure);}
        const outline=el('nav',undefined,'report-outline');outline.setAttribute('aria-label','Canonical report sections');for(const section of selected.content.sections){const a=el('a',section.title);a.href='#canonical-'+section.id;a.addEventListener('click',e=>{e.preventDefault();document.getElementById('canonical-'+section.id)?.scrollIntoView({block:'start'});});outline.append(a);}reading.append(outline);
        for(const section of selected.content.sections){const group=el('section',undefined,'report-section');group.id='canonical-'+section.id;group.append(el('h2',section.title));
          if(/funding|costs/.test(section.id)){const terms=el('p','Figures retain their published year, region and unit. Target-year terms remain unconfirmed; competitive awards are conditional.','report-terms');group.append(terms);}
          for(const item of section.items){
            if(item.type==='table'){
              const table=el('table',undefined,'canonical-table');const caption=el('caption',section.title+' — stated terms and qualifications');table.append(caption);const head=el('thead'),body=el('tbody');
              item.rows.forEach((row,index)=>{const tr=el('tr');for(const block of row){const cell=el(index?'td':'th');if(!index)cell.scope='col';cell.append(blockNode(block,'div'));if(index)sourceControls(block,cell);tr.append(cell);} (index?body:head).append(tr);});table.append(head,body);const wrap=el('div',undefined,'report-table-wrap');wrap.tabIndex=0;wrap.setAttribute('role','region');wrap.setAttribute('aria-label',section.title+' table, scroll horizontally if needed');wrap.append(table);group.append(wrap);
            }else{const box=el('div',undefined,'canonical-passage');if(item.type==='list_item')box.classList.add('canonical-list-item');box.append(blockNode(item.block));sourceControls(item.block,box);group.append(box);}
          }reading.append(group);
        }
        const sourceSection=el('section',undefined,'report-section');sourceSection.id='report-sources';sourceSection.append(el('h2','Sources and editorial evidence map'));
        for(const source of Object.values(selected.content.sources)){const row=el('div',undefined,'report-source');row.id='evidence-'+source.id;row.append(el('h3',source.id+' · '+source.topic),el('p',source.text));for(const link of source.links){const a=el('a',link.label);a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';row.append(a);}sourceSection.append(row);}reading.append(sourceSection);
        repaintMarks();
      }
      function pdfUrl(operation,p=page){return '/api/reports/'+selected.key+'/'+operation+'?edition='+(pdfEdition || selected.edition)+'&page='+p+(pdfSha?'&pdf_sha256='+pdfSha:'');}
      function paintPdfHighlights(){
        const highlights=reading.querySelector('.pdf-highlights');if(!highlights || !pdf)return;highlights.replaceChildren();
        for(const a of annotations.annotations.filter(a=>a.selector.view==='pdf' && a.selector.page===page && a.selector.pdf_sha256===pdf.pdf_sha256))for(const word of pdf.words.filter(w=>w.start<a.selector.end && w.end>a.selector.start)){
          const mark=el('span',undefined,'pdf-mark');mark.dataset.annotation=a.id;Object.assign(mark.style,{left:(100*word.x/pdf.width)+'%',top:(100*word.y/pdf.height)+'%',width:(100*word.width/pdf.width)+'%',height:(100*word.height/pdf.height)+'%'});highlights.append(mark);
        }
      }
      async function renderPdf(){
        clearSelection();const seq=++requestSequence;message('Opening saved PDF…');reading.replaceChildren(el('p','Opening saved PDF page…'));const data=await load(pdfUrl('page'));if(seq!==requestSequence || !article.isConnected)return;pdf=data;download.href=pdfUrl('pdf');reading.replaceChildren();
        const controls=el('div',undefined,'pdf-controls'),pageLabel=el('label','Page '),select=el('select');select.id='pdf-page';for(let n=0;n<pdf.pages;n++){const o=new Option(String(n+1),String(n));select.append(o);}select.value=page;select.addEventListener('change',()=>{page=Number(select.value);renderPdf().catch(e=>message(e.message));});pageLabel.append(select,document.createTextNode(' of '+pdf.pages));controls.append(button('Previous page',async()=>{page=Math.max(0,page-1);await renderPdf();},'pdf-previous'),pageLabel,button('Next page',async()=>{page=Math.min(pdf.pages-1,page+1);await renderPdf();},'pdf-next'));
        const zoom=el('select');zoom.setAttribute('aria-label','PDF zoom');for(const [value,label] of [[1,'Fit width'],[1.25,'125%'],[1.5,'150%'],[2,'200%'],[3,'300%']])zoom.append(new Option(label,String(value)));zoom.addEventListener('change',()=>{canvas.style.width=(Number(zoom.value)*100)+'%';});controls.append(zoom);reading.append(controls,el('p','Select text on this PDF page, then choose Highlight or Comment. Source links are active. For reflowed larger text, switch to Report.','pdf-hint'));
        const viewport=el('div',undefined,'pdf-viewport'),canvas=el('div',undefined,'pdf-page');canvas.dataset.page=page;canvas.style.aspectRatio=pdf.width+'/'+pdf.height;const image=el('img');image.src=pdfUrl('image');image.alt='PDF page '+(page+1)+' of '+pdf.pages;image.draggable=false;const highlights=el('div',undefined,'pdf-highlights'),text=el('div',undefined,'pdf-text-layer');
        for(const [index,word] of pdf.words.entries()){const next=pdf.words[index+1];const gap=next && next.start>=word.end?slice(pdf.text,word.end,next.start):'';const span=el('span',word.text+gap);span.dataset.pdfStart=word.start;span.dataset.pdfEnd=word.end;Object.assign(span.style,{left:100*word.x/pdf.width+'%',top:100*word.y/pdf.height+'%',width:100*word.width/pdf.width+'%',height:100*word.height/pdf.height+'%',fontSize:(100*word.height/pdf.width)+'cqw'});text.append(span);}
        const links=el('div',undefined,'pdf-links');for(const link of pdf.links){const a=el('a');if(link.url){a.href=link.url;a.target='_blank';a.rel='noopener noreferrer';a.setAttribute('aria-label','Open source: '+link.url);}else{a.href='#pdf-page-'+(link.page+1);a.setAttribute('aria-label','Read evidence on PDF page '+(link.page+1));a.addEventListener('click',async event=>{event.preventDefault();page=link.page;await renderPdf();const top=reading.querySelector('.pdf-page');document.getElementById('research-dialog').scrollTop+=top.getBoundingClientRect().top+(link.location?.[1] || 0)*top.clientWidth/pdf.width-toolbar.getBoundingClientRect().height-16;});}Object.assign(a.style,{left:100*link.x/pdf.width+'%',top:100*link.y/pdf.height+'%',width:100*link.width/pdf.width+'%',height:100*link.height/pdf.height+'%'});links.append(a);}canvas.append(image,highlights,text,links);viewport.append(canvas);reading.append(viewport);paintPdfHighlights();message('PDF page '+(page+1)+' of '+pdf.pages+' · selectable text');
      }
      function selection(){
        const chosen=window.getSelection();if(!chosen || chosen.isCollapsed || !chosen.rangeCount){invalidSelection();return;}const range=chosen.getRangeAt(0);
        const parent=node=>node.nodeType===Node.ELEMENT_NODE?node:node.parentElement;
        if(view==='report'){
          const a=parent(range.startContainer)?.closest('[data-report-block]'),b=parent(range.endContainer)?.closest('[data-report-block]');if(!a || a!==b || !reading.contains(a)){invalidSelection('Select within one report paragraph or table cell to annotate.');return;}
          const prefix=range.cloneRange();prefix.selectNodeContents(a);prefix.setEnd(range.startContainer,range.startOffset);const start=chars(prefix.toString()).length,end=start+chars(range.toString()).length;
          const block=selected.content.blocks[a.dataset.reportBlock],quote=slice(block.text,start,end);if(quote!==range.toString()){invalidSelection('Select a passage within one paragraph or table cell.');return;}
          pending={view:'report',block_id:block.id,start,end,quote};
        }else{
          const a=parent(range.startContainer)?.closest('[data-pdf-start]'),b=parent(range.endContainer)?.closest('[data-pdf-start]');if(!a || !b || !reading.contains(a) || !reading.contains(b)){invalidSelection('Select text within the displayed PDF page to annotate.');return;}
          const offset=(element,node,index)=>{const r=document.createRange();r.selectNodeContents(element);r.setEnd(node,index);return chars(r.toString()).length;};
          const start=Number(a.dataset.pdfStart)+offset(a,range.startContainer,range.startOffset),end=Number(b.dataset.pdfStart)+offset(b,range.endContainer,range.endOffset);
          pending={view:'pdf',edition:pdf.edition,pdf_sha256:pdf.pdf_sha256,page,start,end,quote:slice(pdf.text,start,end)};
        }
        if(pending?.quote){message('Passage selected. Choose Highlight or Comment.');highlight.disabled=false;comment.disabled=false;}
      }
      reading.addEventListener('mouseup',selection);reading.addEventListener('touchend',()=>setTimeout(selection,0));reading.addEventListener('keyup',selection);
      function invalidSelection(text){pending=null;highlight.disabled=true;comment.disabled=true;if(text)message(text);}
      function clearSelection(){invalidSelection();window.getSelection()?.removeAllRanges();}
      function showReport(){view='report';++requestSequence;clearSelection();pdfEdition=null;pdfSha=null;download.href=pdfUrl('pdf');renderReport();}
      async function saveSelection(commentText='',selector=pending,closeComment=false){
        if(!selector?.quote)throw Error('Select a passage within one report paragraph, table cell or PDF page first.');
        annotations=await ctx.post('/api/reports/annotate',{key:selected.key,id:crypto.randomUUID(),selector,comment:commentText});if(closeComment)document.getElementById('new-annotation-comment')?.remove();clearSelection();checked.clear();repaintMarks();renderHeader();renderRail();message('Highlight'+(commentText?' and comment':'')+' saved privately for this exact report version.');
      }
      function renderDraft(saved){
        const box=el('section',undefined,'annotation-draft');box.id='annotation-feedback-draft';box.append(el('h3','Review your draft'),el('p','Nothing has been sent. These exact passages, comments and report references will be included. Saving feedback does not invoke Dave.'));
        const label=el('label','Feedback text'),input=el('textarea');input.id='annotation-feedback-text';input.value=saved.comment;input.defaultValue=saved.comment;input.rows=12;input.maxLength=4000;label.htmlFor=input.id;box.append(label,input);
        box.append(button('Save feedback for Dave',async()=>{const feedback=await ctx.post('/api/research/feedback',{...saved.feedback,comment:input.value,submission_key:(saved.lastComment===input.value && saved.submission_key) || (saved.lastComment=input.value,saved.submission_key=crypto.randomUUID())});message('Feedback saved. Copy instructions and invoke Dave manually when ready.');await ctx.handoff(saved.feedback.request_id,feedback.feedback_id);},'send-annotation-feedback'));
        box.append(button('Prepare follow-up request',()=>ctx.openRequest({countries:[code],scope:'refresh',bounds:ctx.current.request.bounds,parent_request_id:ctx.current.request.request_id,parent_request_revision:ctx.current.request.revision,parent_request_digest:ctx.current.request.digest,
          prior_results:[{result_id:saved.feedback.result_id,revision:saved.feedback.revision,digest:saved.feedback.result_digest,finding_id:saved.feedback.finding_id,finding_revision:saved.feedback.finding_revision}],context:input.value,request_only:true}), 'annotation-follow-up'));
        box.append(button('Close draft',()=>{draft=null;renderRail();},'close-annotation-draft'));rail.append(box);
      }
      function renderRail(focusId){
        const dirty=new Map([...rail.querySelectorAll('textarea')].filter(n=>n.value!==n.defaultValue).map(n=>[n.id,n.value]));const commentDraft=rail.querySelector('#new-annotation-comment');rail.hidden=!railOpen;rail.replaceChildren();notesButton.textContent='Annotations ('+annotations.annotations.length+')';notesButton.setAttribute('aria-expanded',String(railOpen));
        rail.append(el('h2','Highlights & comments'),el('p','Private notes on this exact report version. Select annotations to prepare feedback; decisions and factual review are unchanged.'));
        for(const a of annotations.annotations){const box=el('section',undefined,'saved-annotation');box.dataset.annotation=a.id;const choose=el('label'),check=el('input');check.type='checkbox';check.checked=checked.has(a.id);check.addEventListener('change',()=>{check.checked?checked.add(a.id):checked.delete(a.id);});choose.append(check,document.createTextNode(' Include in feedback'));box.append(choose,el('blockquote',a.selector.quote));
          const where=el('button',a.selector.view==='pdf'?'Return to PDF page '+(a.selector.page+1):'Return to passage','annotation-location');where.type='button';where.addEventListener('click',async()=>{if(a.selector.view==='pdf'){view='pdf';page=a.selector.page;if(a.selector.edition!==selected.edition)message('Opening the retained PDF edition this annotation belongs to.');pdfEdition=a.selector.edition;pdfSha=a.selector.pdf_sha256;await renderPdf();}else{showReport();const block=[...reading.querySelectorAll('[data-report-block]')].find(n=>n.dataset.reportBlock===a.selector.block_id);block?.scrollIntoView({block:'center'});}});box.append(where);
          const label=el('label','Comment'),input=el('textarea');input.rows=3;input.value=a.comment;input.defaultValue=a.comment;input.maxLength=2000;input.id='annotation-comment-'+a.id;label.htmlFor=input.id;box.append(label,input);
          box.append(button('Save comment',async()=>{annotations=await ctx.post('/api/reports/annotate',{key:selected.key,id:a.id,comment:input.value});repaintMarks();renderRail(a.id);message('Comment saved.');}),button('Delete annotation',async()=>{annotations=await ctx.post('/api/reports/annotate',{key:selected.key,id:a.id,delete:true});checked.delete(a.id);repaintMarks();renderRail();message('Annotation deleted.');}));rail.append(box);
          if(focusId===a.id)input.focus({preventScroll:true});
        }
        if(!annotations.annotations.length)rail.append(el('p','Select text in the report or PDF, then choose Highlight or Comment.'));
        rail.append(button('Prepare selected feedback',async()=>{draft=await ctx.post('/api/reports/draft',{key:selected.key,annotation_ids:[...checked]});renderRail();},'prepare-annotation-feedback'));
        if(draft)renderDraft(draft);if(commentDraft)rail.prepend(commentDraft);for(const input of rail.querySelectorAll('textarea'))if(dirty.has(input.id) && dirty.get(input.id)!==input.defaultValue)input.value=dirty.get(input.id);
      }
      const reportButton=button('Report',()=>{showReport();message('Canonical report view.');},'reader-show-report'),pdfButton=button('View PDF',async()=>{view='pdf';page=0;pdfEdition=null;pdfSha=null;await renderPdf();},'reader-show-pdf');
      const highlight=button('Highlight',()=>saveSelection(),'reader-highlight');highlight.disabled=true;
      const comment=button('Comment',()=>{if(!pending?.quote)throw Error('Select a passage first.');if(document.getElementById('new-annotation-comment-text')){message('Save or cancel your current comment before starting another.');document.getElementById('new-annotation-comment-text').focus();return;}const selectedPassage={...pending};railOpen=true;renderRail();const box=el('section',undefined,'annotation-draft');box.id='new-annotation-comment';box.append(el('h3','Comment on selected passage'),el('blockquote',selectedPassage.quote));const label=el('label','Your comment'),input=el('textarea');input.id='new-annotation-comment-text';input.rows=4;input.maxLength=2000;label.htmlFor=input.id;box.append(label,input,button('Save highlight and comment',()=>saveSelection(input.value,selectedPassage,true),'save-new-annotation'),button('Cancel',()=>{document.getElementById('new-annotation-comment')?.remove();clearSelection();renderRail();}));rail.prepend(box);input.focus();},'reader-comment');comment.disabled=true;
      const notesButton=button('Annotations (0)',()=>{railOpen=!railOpen;if(railOpen && !rail.children.length)renderRail();else{rail.hidden=!railOpen;notesButton.setAttribute('aria-expanded',String(railOpen));}},'reader-annotations');notesButton.setAttribute('aria-expanded','false');
      const download=el('a','Download PDF','quiet-action');download.id='reader-download-pdf';download.download='';
      const versions=el('select');versions.id='canonical-version';versions.setAttribute('aria-label','Canonical report version');for(const report of reports)versions.append(new Option('Report v'+report.metadata.canonical_document.revision_number+' · '+(report.content.report_date || 'undated'),report.key));
      versions.addEventListener('change',async()=>{try{if(document.getElementById('new-annotation-comment-text') || [...rail.querySelectorAll('textarea')].some(n=>n.value!==n.defaultValue)){versions.value=selected.key;message('Save or cancel your current comment or edited draft before switching versions.');return;}++requestSequence;clearSelection();reading.replaceChildren(el('p','Opening saved report version…'));selected=reports.find(r=>r.key===versions.value);article.dataset.canonical=selected.key;article.dataset.edition=selected.edition;annotations=await load('/api/reports/'+selected.key+'/annotations');pending=null;checked.clear();draft=annotations.draft || null;page=0;pdfEdition=null;pdfSha=null;view='report';download.href=pdfUrl('pdf');renderHeader();renderReport();renderRail();message('Viewing saved report v'+selected.metadata.canonical_document.revision_number+'. Earlier annotations remain bound to their original version.');}catch(e){message(e.message);}});
      toolbar.append(reportButton,pdfButton,highlight,comment,notesButton,download,versions);article.append(header,toolbar,status,content);content.append(reading,rail);
      annotations=await load('/api/reports/'+selected.key+'/annotations');draft=annotations.draft || null;download.href=pdfUrl('pdf');renderHeader();renderReport();renderRail();message('Canonical report loaded. Select a passage to highlight or comment.');
      if(catalog.errors.length)message('A report package needs attention; see Advanced / recovery. The validated report remains available.');
      if(catalog.errors.length){const diagnostics=ctx.technical('Report delivery errors',Object.fromEntries(catalog.errors.map(e=>[e.file,e.error])));ctx.section.querySelector('#report-history')?.append(diagnostics);}
    }catch(error){if(target.isConnected)target.prepend(el('p','Canonical report unavailable: '+error.message+' Original received findings are preserved.','report-package-error'));}
  }
  async function refresh(){
    const article=document.querySelector('.canonical-report');if(!article || article.querySelector('.report-update-ready'))return;
    const catalog=await load('/api/reports?request_id='+article.dataset.request),latest=catalog.reports.find(r=>r.metadata.country_code===article.dataset.country);
    if(!latest || (latest.key===article.dataset.canonical && latest.edition===article.dataset.edition) || !article.isConnected)return;
    const banner=el('div',undefined,'report-update-ready version-warning');banner.append(el('p','An updated canonical report or review is available. Your current annotations remain attached to this version.'));
    const button=el('button','View latest report','quiet-action');button.type='button';button.addEventListener('click',()=>{if(article.querySelector('#new-annotation-comment-text') || [...article.querySelectorAll('textarea')].some(n=>n.value!==n.defaultValue)){article.querySelector('.reader-status').textContent='Save or cancel your comment or edited draft before opening the updated report.';return;}window.GradCompassResearch.openRequests(article.dataset.request);});banner.append(button);article.prepend(banner);
  }
  window.GradCompassReportReader=Object.freeze({upgrade,refresh});
})();
