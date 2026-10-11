#!/usr/bin/env python3
"""Build three claim-linked CV views from one immutable approved profile."""
import argparse, hashlib, json, re, shutil, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = '5.4.0-rendercv-inspired'
VARIANTS = ('master', 'research', 'two_page')

def tex(s):
    esc = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(esc.get(c, c) for c in str(s))

def verify(folder, synthetic):
    boundary = ROOT / ('cv/synthetic' if synthetic else 'private')
    if not folder.resolve().is_relative_to(boundary.resolve()):
        raise ValueError('Source outside permitted storage')
    raw = (folder / 'profile.json').read_bytes()
    p = json.loads(raw)
    r = json.loads((folder / 'receipt.json').read_text())
    digest = hashlib.sha256(raw).hexdigest()
    if (folder / 'COMPLETE').read_text().strip() != 'complete':
        raise ValueError('Missing freeze marker')
    if any(p[k] != r[k] for k in ('profile_id','revision_id','version_name','schema_version')):
        raise ValueError('Source/receipt identity mismatch')
    if p['schema_version'] != '1.0.0' or p['status'] != 'frozen' or bool(p.get('synthetic')) != synthetic:
        raise ValueError('Unsupported source lifecycle')
    if r['sha256'] != digest or r['decision'] != 'accepted' or r['actor_type'] != 'human' or r.get('scope') != 'profile_only':
        raise ValueError('Approval/digest mismatch')
    return p, r, digest

def render(p, selection, variant):
    claims = {}
    for c in p['claims']:
        if c['kind'] in ('documented_fact','user_report','preference') and c.get('value') is not None:
            claims.setdefault((c['subject_id'], c['field']), []).append(c)
    used, audit = set(), []
    def phrase(obj, at):
        if not obj: return ''
        refs = obj.get('refs') or []
        if not refs or not obj.get('text'): raise ValueError(f'Unlinked text at {at}')
        ids = []
        for sid, field in refs:
            found = claims.get((sid,field), [])
            if not found: raise ValueError(f'Missing approved claim at {at}: {sid}/{field}')
            ids.extend(c['id'] for c in found)
        used.update(ids)
        audit.append({'location': at, 'text': obj['text'], 'claim_ids': ids})
        return tex(obj['text'])
    def active(x): return variant in x.get('variants', VARIANTS)
    out = [r'\documentclass[11pt,a4paper]{article}',r'\usepackage{CleanCV}',r'\usepackage[default,type1]{sourcesanspro}',r'\usepackage{fontawesome5}',r'\usepackage{microtype}',r'\usepackage{needspace}',r'\geometry{a4paper,left=2.0cm,right=2.0cm,top=1.8cm,bottom=1.9cm}',r'\definecolor{primary}{RGB}{28,70,105}',r'\hypersetup{urlcolor=primary}',r'\pagestyle{empty}',r'\setlength{\parindent}{0pt}\setlength{\parskip}{0pt}\linespread{1.06}\raggedbottom\frenchspacing',r'\setlist[itemize]{leftmargin=1.3em,label=\textcolor{primary}{\small$\bullet$},nosep,topsep=2pt,itemsep=2pt,parsep=0pt}',r'\newcommand{\cvsection}[1]{\Needspace{6\baselineskip}\vspace{10pt}{\color{primary}\large\bfseries #1}\par\vspace{3pt}{\color{primary}\hrule height 0.55pt}\vspace{6pt}}',r'\newcommand{\cvdated}[2]{\Needspace{3\baselineskip}\begin{tabular*}{\linewidth}{@{}p{0.72\linewidth}@{\extracolsep{\fill}}p{0.25\linewidth}@{}}\textbf{#1}&\raggedleft{\small\color{primary}#2}\end{tabular*}\par}',r'\begin{document}']
    h = selection['header']
    out.append(r'\begin{center}{\fontsize{24}{28}\selectfont\bfseries\color{primary} '+phrase(h['name'],'header.name')+r'}\end{center}\vspace{-8pt}')
    contacts = []
    for x in h.get('contact',[]):
        label=phrase(x,'header.contact')
        raw=x['text']
        target=('mailto:'+raw) if '@' in raw else (raw if raw.startswith('https://') else 'https://'+raw)
        icon=(r'\faEnvelope' if '@' in raw else r'\faGithub' if 'github.com/' in raw else r'\faLinkedin' if 'linkedin.com/' in raw else r'\faLink')
        contacts.append(r'\href{'+tex(target)+r'}{{\color{primary}\footnotesize '+icon+r'}\hspace{3pt}'+label+r'}')
    for i in range(0,len(contacts),3):
        out.append(r'\begin{center}\small '+r'\qquad '.join(contacts[i:i+3])+r'\end{center}\vspace{-7pt}')
    if h.get('tagline'): out.append(r'\begin{center}\small\color{primary} '+phrase(h['tagline'],'header.tagline')+r'\end{center}\vspace{-7pt}')
    for section in selection['sections']:
        if not active(section): continue
        entries = [e for e in section['entries'] if active(e)]
        if not entries: continue
        if section['title'] == 'Publications and Manuscripts': out.append(r'\Needspace{6\baselineskip}')
        out.append(r'\cvsection{'+tex(section['title'])+'}')
        for e in entries:
            key = e['key']
            heading = phrase(e['heading'],key+'.heading')
            date = phrase(e.get('date'),key+'.date')
            if e.get('kind') == 'reference':
                permission = e.get('permission')
                if not permission or permission.get('text') != 'Name, title, affiliation, and professional email.':
                    raise ValueError('Reference publication permission missing')
                phrase(permission,key+'.permission')
                email = phrase(e.get('email'),key+'.email')
                if variant == 'two_page':
                    out.append(r'\Needspace{2\baselineskip}\textbf{'+heading+r'} · \href{mailto:'+tex(e['email']['text'])+'}{'+email+r'}\par\vspace{3pt}')
                else:
                    title = phrase(e.get('title'),key+'.title')
                    department = phrase(e.get('department'),key+'.department')
                    institution = phrase(e.get('institution'),key+'.institution')
                    out.append(r'\Needspace{2\baselineskip}\textbf{'+heading+r'}, '+title+r', '+department+r', '+institution+r' · \href{mailto:'+tex(e['email']['text'])+'}{'+email+r'}\par\vspace{3pt}')
            elif e.get('kind') == 'publication':
                author = phrase(e.get('author'),key+'.author')
                if author and e.get('author_emphasis'):
                    needle=tex(e['author_emphasis'])
                    if needle not in author: raise ValueError('Author emphasis absent from approved author text')
                    author=author.replace(needle,r'\textbf{'+needle+'}',1)
                venue = phrase(e.get('venue'),key+'.venue')
                status = phrase(e.get('status'),key+'.status')
                doi = phrase(e.get('doi'),key+'.doi')
                title=r'\textbf{'+heading+r'}'
                line = []
                if author: line.append(author+'.')
                if venue: line.append(r'\emph{'+venue+'}.')
                if date: line.append(date+'.')
                if status: line.append(status+'.')
                if doi:
                    raw=e['doi']['text']
                    target=raw if raw.startswith('https://') else 'https://doi.org/'+raw.removeprefix('DOI:').strip()
                    title=r'\href{'+tex(target)+r'}{'+title+r'}'
                    line.append('DOI: '+r'\href{'+tex(target)+r'}{'+doi+'}.')
                out.append(r'\Needspace{5\baselineskip}'+title+r'\par{\small '+' '.join(line)+r'}\par\vspace{8pt}')
            else:
                sub = phrase(e.get('subline'),key+'.subline')
                bullets = [b for b in e.get('bullets',[]) if active(b)]
                out.append(r'\Needspace{'+str(3+len(bullets))+r'\baselineskip}')
                if e.get('indent'):
                    out.append(r'\hspace*{1.3em}\begin{minipage}{\dimexpr\linewidth-1.3em\relax}')
                out.append(r'\cvdated{'+heading+'}{'+date+'}')
                if sub: out.append(r'{\small\itshape '+sub+r'}\par')
                if bullets:
                    out.append(r'\begin{itemize}')
                    for i,b in enumerate(bullets): out.append(r'\item '+phrase(b,key+f'.bullet{i}'))
                    out.append(r'\end{itemize}')
                if e.get('indent'):
                    out.append(r'\end{minipage}\par')
                out.append(r'\vspace{6pt}')
    out.append(r'\end{document}')
    return '\n'.join(out), sorted(used), audit

def main():
    ap=argparse.ArgumentParser()
    for x in ('frozen','selection','out'): ap.add_argument('--'+x,type=Path,required=True)
    ap.add_argument('--synthetic',action='store_true')
    a=ap.parse_args()
    p,r,digest=verify(a.frozen,a.synthetic)
    boundary=ROOT/('cv/synthetic' if a.synthetic else 'private')
    if not a.selection.resolve().is_relative_to(boundary.resolve()) or not a.out.resolve().is_relative_to(boundary.resolve()):
        raise ValueError('Selection/output outside permitted storage')
    sel=json.loads(a.selection.read_text())
    a.out.mkdir(parents=True,exist_ok=True)
    shutil.copy2(ROOT/'cv/vendor/cleancv/CleanCV.sty',a.out/'CleanCV.sty')
    shutil.copy2(ROOT/'cv/vendor/cleancv/LICENSE',a.out/'CleanCV-LICENSE')
    manifest={'source':{k:p[k] for k in ('profile_id','revision_id','version_name','schema_version')},'sha256':digest,'receipt_id':r['receipt_id'],'template_build_version':VERSION,'selection_sha256':hashlib.sha256(a.selection.read_bytes()).hexdigest(),'built_at_utc':datetime.now(timezone.utc).isoformat(),'variants':{}}
    full_audit={}
    for v in VARIANTS:
        source,used,audit=render(p,sel,v)
        path=a.out/(v+'.tex'); path.write_text(source)
        subprocess.run(['pdflatex','-interaction=nonstopmode','-halt-on-error','-output-directory',str(a.out),str(path)],check=True,stdout=subprocess.DEVNULL)
        info=subprocess.check_output(['pdfinfo',str(a.out/(v+'.pdf'))],text=True)
        pages=int(re.search(r'^Pages:\s+(\d+)',info,re.M).group(1))
        manifest['variants'][v]={'pages':pages,'claim_ids':used,'source':v+'.tex','pdf':v+'.pdf'}
        full_audit[v]=audit
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (a.out/'claim-audit.json').write_text(json.dumps(full_audit,indent=2)+'\n')
    if not a.synthetic and manifest['variants']['two_page']['pages'] != 2:
        raise ValueError('Concise CV must render to exactly two pages')
    print({v:manifest['variants'][v]['pages'] for v in VARIANTS})
if __name__=='__main__': main()
