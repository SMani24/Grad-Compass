#!/usr/bin/python3
"""Use Paperclip's native service manager with this owner's pinned local runtime.

Configure runtime/paperclip-service/launch.local.json once; no shell, downloads,
agent credentials or application configuration changes are involved.
"""
import json
import os
from pathlib import Path
import socket
import stat
import sys
import urllib.request
from uuid import UUID

SETTINGS = Path(__file__).resolve().parents[2] / 'grad-compass-workspace/runtime/paperclip-service/launch.local.json'
RUNTIME_ENVIRONMENT = frozenset(('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY',
    'http_proxy', 'https_proxy', 'all_proxy', 'no_proxy', 'CODEX_INTERNAL_ORIGINATOR_OVERRIDE'))


def read_control(port, path):
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):return None
    headers={}
    token=os.environ.get('GRAD_COMPASS_PAPERCLIP_TOKEN')
    if token:headers['Authorization']='Bearer '+token
    request=urllib.request.Request('http://127.0.0.1:'+str(port)+'/api'+path,headers=headers)
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect)
    try:
        with opener.open(request,timeout=5) as response:raw=response.read(4_000_001)
        if len(raw)>4_000_000:raise ValueError('Oversized control response')
        return json.loads(raw)
    except (OSError,ValueError):
        raise ValueError('Cannot verify idle Paperclip execution state. Inspect service status and existing work before maintenance; no restart was performed.') from None


def assert_idle(port):
    if type(port) is not int or not 1024<=port<=65535:raise ValueError('Invalid pinned controller port; no restart was performed.')
    companies=read_control(port,'/companies')
    if not isinstance(companies,list) or len(companies)>64:
        raise ValueError('Cannot verify idle Paperclip execution state; no restart was performed.')
    for company in companies:
        if not isinstance(company,dict):raise ValueError('Invalid controller state; no restart was performed.')
        identity=str(UUID(str(company.get('id',''))))
        live=read_control(port,'/companies/'+identity+'/live-runs')
        if not isinstance(live,list):raise ValueError('Cannot verify active executions; no restart was performed.')
        if live:raise ValueError('Research work is still active. No restart was performed. Let existing work finish, then retry planned maintenance.')


def main():
    try:
        info = SETTINGS.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Runtime settings must be an owner-private regular file')
        settings = json.loads(SETTINGS.read_text())
        paths = {key: Path(settings[key]) for key in ('node', 'entrypoint', 'config')}
        if any(not p.is_absolute() or not p.is_file() for p in paths.values()):
            raise ValueError('Configured runtime files are unavailable')
        codex_home = Path(settings['codex_home'])
        if not codex_home.is_absolute() or not codex_home.is_dir():
            raise ValueError('The existing Codex credential/configuration home is unavailable')
        args = sys.argv[1:]
        if not args:
            raise ValueError('Specify a native Paperclip command, for example service status --json')
        if args[:2] == ['service', 'restart']:
            assert_idle(settings['port'])
            # Legacy task executions were actually orphaned by non-draining
            # native restarts. Do not assume native-session adoption covers them.
            if '--wait' not in args:args += ['--wait']
        if args[0] == 'run':
            if any(a in ('--force', '--repair', '--config', '-c', '--data-dir', '-d') or a.startswith(('--config=', '--data-dir=')) for a in args):
                raise ValueError('The service uses its pinned configuration without automatic repairs')
            args += ['--no-repair', '--config', str(paths['config'])]
            port = settings['port']
            if type(port) is not int or not 1024 <= port <= 65535:
                raise ValueError('Specify the app connection port explicitly')
            # Native Paperclip otherwise falls forward to another port while
            # sharing the same database with an existing foreground controller.
            with socket.socket() as probe:
                probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    probe.bind(('127.0.0.1', port))
                except OSError:
                    raise ValueError('The configured Paperclip port is unavailable. Inspect the existing controller; do not start a parallel instance.') from None
        environment = dict(os.environ)
        environment['PAPERCLIP_SHIM_PATH'] = str(Path(__file__).resolve())
        # A login service does not inherit the development client's environment.
        # Select the existing credential store; never copy secrets or change models.
        environment['CODEX_HOME'] = str(codex_home)
        runtime_environment = settings.get('runtime_environment', {})
        if not isinstance(runtime_environment, dict) or any(k not in RUNTIME_ENVIRONMENT or not isinstance(v, str) for k, v in runtime_environment.items()):
            raise ValueError('Only existing non-secret routing/client settings may be pinned')
        environment.update(runtime_environment)
        environment['PATH'] = str(paths['node'].parent) + os.pathsep + environment.get('PATH', os.defpath)
        if args[0] == 'run':
            environment['PORT'] = str(port)
        os.umask(0o077)
        os.execve(paths['node'], [str(paths['node']), str(paths['entrypoint']), *args], environment)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print('Paperclip local runtime unavailable: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
