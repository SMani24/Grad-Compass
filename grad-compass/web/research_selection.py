"""Private research draft scope, independent of saved membership and research history."""
from contextlib import closing
from web.country_evidence import COUNTRY_CODES
from web import research_envelopes as env
from web.local import atomic_json, regular


def selection(workspace, payload=None):
    # Snapshots/export can already hold this reentrant lock; backups take it too.
    with workspace.research.lock, closing(workspace.connect()):
        path = regular(workspace.directory / 'research-selection.json')
        value = env.loads(path.read_bytes()) if path.exists() else {'countries': []}
        candidate = payload if payload is not None else value
        countries = candidate.get('countries') if isinstance(candidate, dict) else None
        if (not isinstance(candidate, dict) or set(candidate) != {'countries'}
            or not isinstance(countries, list) or len(countries) > len(COUNTRY_CODES)
            or any(not isinstance(code, str) or code not in COUNTRY_CODES for code in countries)
            or len(set(countries)) != len(countries)):
            raise ValueError('Select distinct countries and territories from the catalogue')
        if payload is not None:
            atomic_json(path, candidate)
        return candidate
