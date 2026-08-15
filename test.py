import requests
import sys

try:
    r = requests.head('http://bfts.5read.com/pdz/15431837unRegister.pdz', timeout=10)
    print('Status Code:', r.status_code)
    print('Headers:', dict(r.headers))
    sys.exit(0)
except Exception as e:
    print('Error:', e)
    sys.exit(1)
