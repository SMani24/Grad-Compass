"""Read-only deliverable projection; publication is not execution or acceptance."""


def countries(codes, reports, requires_reports=True):
    output=[]
    for code in codes:
        report=reports.get(code);model=report['model'] if report else {}
        checks=model.get('delivery_checks',{});pending=[]
        if not report and requires_reports:pending.append({'item':'Prepared report','owner':'Dave / research team','action':'Prepare, review and publish the existing request’s editions.'})
        elif report and model['preparation']['overview']!='published':pending.append({'item':'Concise edition','owner':'Dave / research team','action':model['preparation']['overview_reason']})
        if report and checks.get('photo')!='available':
            pending.append({'item':'Country photograph','owner':'Ali; packaging Marry',
                'reason':checks.get('photo_reason'),
                'action':'Acquire a licensed photograph, record provenance and publish reviewed offline bytes; record any genuine failure and its recovery action.'})
        output.append({'country':code,'available':bool(report),'required':requires_reports,'version':model.get('version_label'),
            'review':model.get('review'),'overview':model.get('preparation',{}).get('overview'),
            'photo':checks.get('photo','not_yet_published'),'outstanding':pending,
            'coverage':model.get('coverage',[]),'key':report['key'] if report else None,
            'edition':report['edition'] if report else None})
    return output


def summary(rows, completion):
    ready=sum(row['available'] for row in rows)
    pending=sum(len(row['outstanding']) for row in rows)
    return {'published':ready,'total':len(rows),'outstanding_count':pending,
        'response_completion':completion,
        'label':f'{ready}/{len(rows)} reports published · '+('bounded response complete' if completion=='complete' else 'response partial' if completion=='partial' else 'awaiting response'),
        'qualification':'Report availability, outstanding deliverables, research uncertainty and review are separate. Completion covers the saved scope, not exhaustive country research.'}
