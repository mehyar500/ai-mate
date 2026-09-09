"""Start the local MVP with python -m local_app."""
import argparse
import json
import sys
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--rtc', action='store_true', help='Enable experimental same-PC WebRTC calls.')
    parser.add_argument('--check', action='store_true', help='Check readiness without exposing memory or credentials.')
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be between 1 and 65535')
    if args.check:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/bootstrap', timeout=5) as response:
                state = json.load(response)
            print(json.dumps({'reachable': True, 'ready': bool(state.get('ready')),
                              'video_ready': bool(state.get('visual_loaded')) and not bool(state.get('visual_error')),
                              'busy': bool(state.get('busy'))}))
            return 0 if state.get('ready') and state.get('visual_loaded') and not state.get('visual_error') else 1
        except (OSError, ValueError):
            print('Local demo unavailable. Run ./scripts/start_local.ps1 -Background.')
            return 1
    from .server import main as serve
    # The HTTP server retains its established argument handling.
    sys.argv = [sys.argv[0], '--port', str(args.port)] + (['--rtc'] if args.rtc else [])
    serve()
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
