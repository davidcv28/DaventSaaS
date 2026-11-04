import http.server, urllib.request
class H(http.server.BaseHTTPRequestHandler):
    def _harness(self):
        html = open('host-test.html','rb').read()
        self.send_response(200); self.send_header('Content-Type','text/html'); self.end_headers()
        self.wfile.write(html)
    def _relay(self, method):
        if self.path.startswith('/host-test'): return self._harness()
        url = 'http://127.0.0.1:8000' + self.path
        req = urllib.request.Request(url, method='GET')
        for k,v in self.headers.items():
            if k.lower() not in ('host','content-length','connection'): req.add_header(k,v)
        try:
            res = urllib.request.urlopen(req, timeout=30); code,data,hdrs = res.status,res.read(),res.headers
        except urllib.error.HTTPError as e:
            code,data,hdrs = e.code,e.read(),e.headers
        self.send_response(code)
        for k,v in hdrs.items():
            if k.lower() in ('x-frame-options','content-security-policy','transfer-encoding','connection'): continue
            self.send_header(k,v)
        self.end_headers(); self.wfile.write(data)
    do_GET = lambda s: s._relay('GET')
    def log_message(self,*a): pass
http.server.HTTPServer(('127.0.0.1',8792),H).serve_forever()
