"""Check a running Python API without registering users or modifying data."""
import json
import urllib.request
from urllib.error import URLError
for path in ['/api/v1/health','/api/v1/config','/openapi.json']:
    try:
        with urllib.request.urlopen('http://localhost:8000'+path,timeout=5) as response:
            data=json.load(response)
        print(path, 'OK', f"({len(data['paths'])} paths)" if 'paths' in data else data)
    except URLError as error:
        raise SystemExit(f'Cannot reach the API: {error}. Start the local application first.')
