# Mubasher-only data shim for the REPAIR-003 ORAS.CA cell re-run.
# Serves ORAS.CA Yahoo-chart-shaped JSON built ONLY from the saved
# Mubasher chartData response; every other Yahoo request fails, so
# no Yahoo bar can enter the run. Runner code is untouched.
import io, json, os, sys
sys.modules["yahooquery"] = None  # forces the runners' chart-API path
RAW = os.environ.get("MUBASHER_RAW", "/tmp/rn/mubasher_oras_raw.json")

def _payload():
    d = json.load(open(RAW))["data"]
    d = sorted(d, key=lambda x: x["time"])
    ts = [x["time"] for x in d]
    q = {"open": [x["open"] for x in d], "high": [x["highPrice"] for x in d],
         "low": [x["lowPrice"] for x in d], "close": [x["closePrice"] for x in d],
         "volume": [x["volume"] for x in d]}
    return {"chart": {"result": [{"meta": {"exchangeTimezoneName": "UTC",
            "symbol": "ORAS.CA", "dataSource": "mubasher"},
            "timestamp": ts, "indicators": {"quote": [q]},
            "events": {"dividend": {}}}], "error": None}}

def _match(url):
    return "finance/chart/ORAS.CA" in url

class _Resp:
    status_code = 200
    def __init__(self, body): self._b = body
    def json(self): return json.loads(self._b)
    def raise_for_status(self): pass
    def read(self): return self._b
    def __enter__(self): return self
    def __exit__(self, *a): return False

def _guard(url):
    if "yahoo" in url:
        if _match(url):
            return json.dumps(_payload()).encode()
        raise RuntimeError("blocked non-ORAS Yahoo request: " + url)
    return None

import urllib.request as _ur
_orig_urlopen = _ur.urlopen
def urlopen(req, *a, **k):
    url = req if isinstance(req, str) else req.full_url
    b = _guard(url)
    return _Resp(b) if b is not None else _orig_urlopen(req, *a, **k)
_ur.urlopen = urlopen
try:
    import requests
    _orig_get = requests.get
    def get(url, *a, **k):
        b = _guard(url)
        return _Resp(b) if b is not None else _orig_get(url, *a, **k)
    requests.get = get
except Exception:
    pass
