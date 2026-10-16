"""Restore a verified local backup into a NEW workspace, preserving the current one."""
import argparse
from pathlib import Path
import sys
APP_ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(APP_ROOT))
from web.recovery import restore_backup


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('backup',type=Path)
    parser.add_argument('destination',type=Path)
    args=parser.parse_args()
    workspace=restore_backup(args.backup,args.destination)
    print('Restored private workspace:',workspace.directory)
    print('Open with:',sys.executable,'-B',APP_ROOT/'scripts/launch_preview.py','--local-dir',workspace.directory)


if __name__=='__main__':main()
