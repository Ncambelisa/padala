#!/usr/bin/env python3
"""Install and run Padala locally. No admin rights or paid provider keys required.
Usage: python run_local.py --demo
Keep this terminal open; Ctrl+C stops both servers. Does not expose the app publicly.
"""
from __future__ import annotations
import argparse
import ipaddress
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
import venv
import webbrowser

ROOT=Path(__file__).resolve().parent

def execute(command, cwd=ROOT, env=None):
    print('>', ' '.join(str(c) for c in command), flush=True)
    subprocess.run([str(c) for c in command],cwd=cwd,env=env,check=True,
                   shell=(os.name=='nt' and str(command[0]).lower().endswith(('.cmd','.bat'))))

def port_free(port):
    with socket.socket() as s:
        try:s.bind(('127.0.0.1',port));return True
        except OSError:return False

def main():
    parser=argparse.ArgumentParser(description='Install and start the Padala Next.js + Python app.')
    parser.add_argument('--demo',action='store_true',help='Use an isolated fictional household in backend/demo-data.')
    parser.add_argument('--no-install',action='store_true',help='Skip dependency installation after the first setup.')
    parser.add_argument('--install-only',action='store_true')
    parser.add_argument('--no-browser',action='store_true')
    parser.add_argument('--lan-ip',help='Your private IPv4 address for an optional same-Wi-Fi demonstration. No private real data over HTTP.')
    parser.add_argument('--web-port',type=int,default=3000)
    parser.add_argument('--api-port',type=int,default=8000)
    args=parser.parse_args()
    if sys.version_info<(3,11):raise SystemExit('Python 3.11 or newer is required.')
    node=shutil.which('node');npm=shutil.which('npm')
    if not node or not npm:raise SystemExit('Install Node.js 22 LTS or newer (including npm), reopen your terminal, and run this script again.')
    major=int(subprocess.check_output([node,'--version'],text=True).strip().lstrip('v').split('.')[0])
    if major<22:raise SystemExit('This project requires Node.js 22 or newer.')
    for port in [args.web_port,args.api_port]:
        if not 1024<=port<=65535:raise SystemExit('Use ports from 1024 through 65535.')
        if not args.install_only and not port_free(port):raise SystemExit(f'Port {port} is in use. Stop that service or choose another port.')
    if args.web_port==args.api_port:raise SystemExit('The web and API ports must be different.')
    if args.lan_ip:
        addr=ipaddress.ip_address(args.lan_ip)
        if addr.version!=4 or not addr.is_private or addr.is_loopback:raise SystemExit('--lan-ip must be the private IPv4 address of this computer.')
        print('LAN demo mode: use only fictional data on a trusted Wi-Fi network. HTTP is not encrypted.')
    for example,target in [(ROOT/'backend/.env.example',ROOT/'backend/.env'),(ROOT/'frontend/.env.local.example',ROOT/'frontend/.env.local')]:
        if not target.exists():shutil.copyfile(example,target)
    envpath=ROOT/'.venv'
    py=envpath/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    if not py.exists():
        print('Creating isolated Python environment…',flush=True);venv.create(envpath,with_pip=True)
    if not args.no_install:
        execute([py,'-m','pip','install','-r','requirements.txt'],ROOT/'backend')
        execute([npm,'install'],ROOT/'frontend')
    nextcli=ROOT/'frontend/node_modules/next/dist/bin/next'
    if not nextcli.exists():raise SystemExit('Next.js dependencies are missing. Run without --no-install on a network that can reach npm.')
    env=os.environ.copy()
    if args.demo:env['DATA_DIR']=str(ROOT/'backend/demo-data')
    apphost=args.lan_ip or 'localhost'
    env['APP_URL']=f'http://{apphost}:{args.web_port}'
    env['ALLOWED_ORIGINS']=','.join(dict.fromkeys([f'http://localhost:{args.web_port}',f'http://127.0.0.1:{args.web_port}',f'http://{apphost}:{args.web_port}',f'http://localhost:{args.api_port}',f'http://127.0.0.1:{args.api_port}']))
    env['API_INTERNAL_URL']=f'http://127.0.0.1:{args.api_port}'
    env['NEXT_TELEMETRY_DISABLED']='1'
    execute([py,'-m','app.cli','seed' if args.demo else 'init'],ROOT/'backend',env)
    if args.install_only:
        print('Setup complete. Run again with --no-install and the same --demo choice.');return
    processes=[]
    try:
        # Bind the API to loopback even for a LAN demo. The browser reaches it through Next.
        processes.append(subprocess.Popen([str(py),'-m','uvicorn','app.main:app','--host','127.0.0.1','--port',str(args.api_port),'--no-access-log'],cwd=ROOT/'backend',env=env))
        processes.append(subprocess.Popen([node,str(nextcli),'dev','--hostname','0.0.0.0' if args.lan_ip else '127.0.0.1','--port',str(args.web_port)],cwd=ROOT/'frontend',env=env))
        url=f'http://{apphost}:{args.web_port}'
        print(f'\nWeb app: {url}\nAPI documentation: http://localhost:{args.api_port}/docs\nKeep this terminal open. Ctrl+C stops both servers.\n',flush=True)
        opened=False
        while all(p.poll() is None for p in processes):
            if not opened:
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{args.web_port}',timeout=2).close()
                    if not args.no_browser:webbrowser.open(url)
                    opened=True
                except (OSError,TimeoutError):pass
            time.sleep(1)
        failed=next((p.returncode for p in processes if p.poll() is not None),1)
        if failed:raise SystemExit(f'A service stopped (exit {failed}). Read the terminal error above.')
    except KeyboardInterrupt:
        print('\nStopping Padala…')
    finally:
        for p in processes:
            if p.poll() is None:p.terminate()
        for p in processes:
            try:p.wait(timeout=8)
            except subprocess.TimeoutExpired:p.kill()

if __name__=='__main__':
    try:main()
    except subprocess.CalledProcessError as exc:
        raise SystemExit(f'Command failed (exit {exc.returncode}). Check internet access, package versions, and the error shown above.')
