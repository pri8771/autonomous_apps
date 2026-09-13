"""Runtime composition tests; fake Stripe and page HTML, real SQLite/WSGI/HTTP."""
import copy
import hashlib
import io
import json
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch, Mock
from urllib.request import Request, urlopen
from wsgiref.simple_server import make_server

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'operator'))
import checkout_runtime as cr
import report_fetch as rf
import stripe_checkout as sc
from private_intake import validate_intake_request
from test_stripe_checkout import FakeStripe, NOW, WEBHOOK_SECRET, sign

KEY = 'a' * 43
ORIGIN = 'http://127.0.0.1:8765'


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = sc.StripeConfig('test', 'sk_test_fixture', WEBHOOK_SECRET, Path(self.tmp.name) / 'payments.sqlite',
            'https://priyanshchordia.com/commercelint/inquiry.html?payment=return',
            'https://priyanshchordia.com/commercelint/inquiry.html?payment=cancel')
        self.provider = FakeStripe()
        self.client = sc.StripeCheckout(self.config, transport=self.provider, clock=lambda: NOW)
        self.html = (ROOT / 'tests/fixtures/strong.html').read_text()
        self.fetcher = Mock(return_value=self.html)
        self.runtime = cr.CheckoutRuntime(self.client, delivery_key=KEY, origin=ORIGIN, fetcher=self.fetcher, clock=lambda: NOW)
        def without_dns(**kwargs):
            kwargs['resolve_dns'] = False
            return validate_intake_request(**kwargs)
        p = patch.object(sc, 'validate_intake_request', side_effect=without_dns)
        p.start(); self.addCleanup(p.stop)

    def request(self, path, body=None, token='', origin=ORIGIN, method='POST', raw=None, **extra):
        raw = json.dumps(body or {}).encode() if raw is None else raw
        env = {'PATH_INFO': path, 'REQUEST_METHOD': method, 'CONTENT_LENGTH': str(len(raw)), 'CONTENT_TYPE': 'application/json',
            'HTTP_ORIGIN': origin, 'HTTP_AUTHORIZATION': 'Bearer ' + token, 'wsgi.input': io.BytesIO(raw), **extra}
        result = []
        output = b''.join(self.runtime.application(env, lambda status, headers: result.extend([status, dict(headers)])))
        return result[0], json.loads(output), result[1]

    def checkout(self, request_id='runtime-test-00000001'):
        status, data, headers = self.request('/inquiry', {'request_id': request_id, 'plan_id': 'sample',
            'urls': ['https://example.com/product'], 'contact_email': 'buyer@example.com'})
        self.assertEqual(status, '200 OK')
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['Access-Control-Allow-Origin'], ORIGIN)
        return data

    def pay(self):
        session = copy.deepcopy(next(iter(self.provider.sessions.values())))
        session.update(status='complete', payment_status='paid')
        event = {'id': 'evt_runtime1', 'type': 'checkout.session.completed', 'livemode': False, 'data': {'object': session}}
        raw, signature = sign(event)
        return self.request('/webhook', raw=raw, HTTP_STRIPE_SIGNATURE=signature)

    def test_complete_private_delivery_receipt_and_replay(self):
        order = self.checkout(); oid, token = order['order_id'], order['report_token']
        self.assertEqual(self.checkout()['report_token'], token)
        self.assertEqual(self.runtime.work_once(), {'status': 'idle'})
        self.assertEqual(self.request('/report', {'order_id': oid}, token)[1]['status'], 'pending_checkout')
        self.assertEqual(self.pay()[0], '200 OK'); self.assertTrue(self.pay()[1]['duplicate'])
        self.assertEqual(self.runtime.work_once()['status'], 'report_available')
        self.fetcher.assert_called_once_with('https://example.com/product')
        status, report, headers = self.request('/report', {'order_id': oid}, token)
        self.assertEqual(status, '200 OK'); self.assertIn('CommerceLint', report['markdown'])
        self.assertNotIn('buyer@example.com', json.dumps(report))
        self.assertEqual(report['artifact_sha256'], hashlib.sha256(report['markdown'].encode()).hexdigest())
        ack = {'order_id': oid, 'artifact_sha256': report['artifact_sha256']}
        self.assertEqual(self.request('/acknowledge', ack, token)[1]['status'], 'client_receipt_recorded')
        self.assertEqual(self.request('/acknowledge', ack, token)[0], '200 OK')
        self.assertEqual(self.runtime.work_once()['status'], 'idle')
        with self.client._db() as db:
            self.assertEqual(db.execute('SELECT received_at FROM report_access').fetchone()[0], NOW)
            self.assertEqual(db.execute('SELECT delivery_status FROM jobs').fetchone()[0], 'not_delivered')

    def test_no_order_only_wrong_token_cross_order_or_expired_access(self):
        first = self.checkout(); second = self.checkout('runtime-test-00000002')
        self.pay(); self.runtime.work_once()
        for oid, token in [(first['order_id'], ''), (first['order_id'], second['report_token']), (second['order_id'], first['report_token'])]:
            self.assertEqual(self.request('/report', {'order_id': oid}, token)[0], '400 Bad Request')
        self.runtime.clock = lambda: NOW + 31 * 86400
        self.assertEqual(self.request('/report', {'order_id': first['order_id']}, first['report_token'])[0], '400 Bad Request')
        self.assertEqual(self.checkout()['report_token'], first['report_token'])
        self.assertEqual(self.request('/report', {'order_id': first['order_id']}, first['report_token'])[0], '400 Bad Request')

    def test_fetch_failure_retries_bounded_and_restart_recovers(self):
        order = self.checkout(); self.pay()
        self.fetcher.side_effect = rf.FetchError('synthetic')
        for attempt in range(3):
            self.runtime.clock = lambda: NOW + attempt * 301
            self.assertEqual(self.runtime.work_once()['status'], 'retry_or_support_required')
        self.assertEqual(self.runtime.work_once()['status'], 'idle')
        self.assertEqual(self.request('/report', {'order_id': order['order_id']}, order['report_token'])[1]['status'], 'support_required')
        with self.client._db() as db:
            db.execute('UPDATE runtime_jobs SET error=NULL,retry_at=?', (NOW - 1,))
        self.assertEqual(self.request('/report', {'order_id': order['order_id']}, order['report_token'])[1]['status'], 'support_required')
        self.assertEqual(self.fetcher.call_count, 3)
        with self.client._db() as db:
            self.assertIsNone(db.execute('SELECT report_markdown FROM jobs').fetchone()[0])

    def test_active_lease_excludes_concurrent_worker_and_stale_lease_recovers(self):
        self.checkout(); self.pay()
        started, release = threading.Event(), threading.Event()
        def blocking_fetch(url):
            started.set(); release.wait(5); return self.html
        self.runtime.fetcher = blocking_fetch
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(self.runtime.work_once)
            self.assertTrue(started.wait(2))
            self.assertEqual(self.runtime.work_once()['status'], 'idle')
            release.set(); self.assertEqual(first.result()['status'], 'report_available')
        with self.client._db() as db:
            db.execute("UPDATE jobs SET status='queued',report_markdown=NULL")
            db.execute("UPDATE runtime_jobs SET lease_id='crashed',retry_at=?,attempts=1", (NOW - 1,))
        restarted = cr.CheckoutRuntime(sc.StripeCheckout(self.config, transport=self.provider), delivery_key=KEY,
            origin=ORIGIN, fetcher=self.fetcher, clock=lambda: NOW)
        self.assertEqual(restarted.work_once()['status'], 'report_available')

    def test_request_boundaries_and_no_public_tokens(self):
        order = self.checkout()
        for body in ([], {'order_id': []}, {'order_id': order['order_id'], 'token': order['report_token']}):
            self.assertEqual(self.request('/report', body, order['report_token'])[0], '400 Bad Request')
        self.assertEqual(self.request('/inquiry', {}, origin='https://evil.example')[0], '400 Bad Request')
        self.assertEqual(self.request('/inquiry', raw=b'{invalid')[0], '400 Bad Request')
        self.assertEqual(self.request('/report', CONTENT_LENGTH='999999')[0], '400 Bad Request')
        self.assertEqual(self.request('/health', method='GET')[1], {'status': 'ok', 'mode': 'test'})
        self.assertEqual(self.request('/report/' + order['order_id'], method='GET')[0], '404 Not Found')

    def test_config_no_network_key_change_and_private_file(self):
        with self.assertRaises(sc.PaymentError):
            cr.CheckoutRuntime(self.client, delivery_key='b'*43, origin=ORIGIN)
        with self.assertRaises(sc.PaymentError):
            cr.CheckoutRuntime(self.client, delivery_key=KEY, origin='http://example.com')
        path = Path(self.tmp.name) / 'runtime.json'
        path.write_text(json.dumps({'COMMERCELINT_TEST_SETTING': 'protected-fixture'})); path.chmod(0o644)
        with self.assertRaises(sc.PaymentError): cr.load_protected_environment(path)
        path.chmod(0o600)
        with patch.dict(os.environ, {}, clear=True):
            cr.load_protected_environment(path)
            self.assertEqual(os.environ['COMMERCELINT_TEST_SETTING'], 'protected-fixture')
        alias = path.with_name('alias'); alias.symlink_to(path)
        with self.assertRaises(sc.PaymentError): cr.load_protected_environment(alias)
        self.assertEqual(self.provider.calls, [])

    def test_real_loopback_http_roundtrip(self):
        with make_server('127.0.0.1', 0, self.runtime.application, handler_class=cr.QuietHandler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            try:
                base = f'http://127.0.0.1:{server.server_port}'
                with urlopen(base + '/health', timeout=2) as r:
                    self.assertEqual(json.load(r)['mode'], 'test')
                with urlopen(base + '/', timeout=2) as r:
                    self.assertIn(b'CommerceLint private report checkout', r.read())
                body = json.dumps({'request_id':'loopback-request-00001','plan_id':'sample','urls':['https://example.com/product'],'contact_email':'buyer@example.com'}).encode()
                request = Request(base + '/inquiry', data=body, headers={'Origin':ORIGIN,'Content-Type':'application/json'})
                with urlopen(request, timeout=2) as r: order=json.load(r)
                self.pay(); self.runtime.work_once()
                request = Request(base + '/report', data=json.dumps({'order_id':order['order_id']}).encode(),
                    headers={'Origin':ORIGIN,'Content-Type':'application/json','Authorization':'Bearer '+order['report_token']})
                with urlopen(request, timeout=2) as r:
                    self.assertEqual(json.load(r)['status'], 'report_available')
            finally: server.shutdown(); thread.join(2)

    def test_environment_entrypoints_and_safe_storage_failure(self):
        settings = {'COMMERCELINT_STRIPE_MODE':'test','COMMERCELINT_STRIPE_TEST_SECRET_KEY':'sk_test_fixture',
            'COMMERCELINT_STRIPE_TEST_WEBHOOK_SECRET':WEBHOOK_SECRET,'COMMERCELINT_STRIPE_TEST_DB_PATH':str(self.config.database_path),
            'COMMERCELINT_CHECKOUT_SUCCESS_URL':self.config.success_url,'COMMERCELINT_CHECKOUT_CANCEL_URL':self.config.cancel_url,
            'COMMERCELINT_DELIVERY_KEY':KEY,'COMMERCELINT_RUNTIME_ORIGIN':ORIGIN}
        with patch.dict(os.environ,settings,clear=True), patch.object(sys,'argv',['runtime','check-config']), patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(cr.main(),0)
            self.assertEqual(json.loads(output.getvalue()),{'status':'configuration_valid','mode':'test','provider_contacted':False})
            self.assertTrue(callable(cr.create_application()))
        with patch.object(cr,'runtime_from_environment',side_effect=sqlite3.OperationalError('private detail must not print')), patch.object(sys,'argv',['runtime','check-config']), patch('sys.stdout',new_callable=io.StringIO) as output:
            self.assertEqual(cr.main(),2)
            self.assertNotIn('private detail',output.getvalue())


class SafeFetchTests(unittest.TestCase):
    def test_accepted_unicode_url_encodes_wire_target_without_double_escaping(self):
        url = 'http://example.com/products/café?q=été&path=a%20b'
        self.assertTrue(validate_intake_request(plan_id='sample',urls=[url],contact_email='buyer@example.com',resolve_dns=False)['charge_allowed'])
        client, server = socket.socketpair()
        self.addCleanup(client.close); self.addCleanup(server.close)
        server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 15\r\nConnection: close\r\n\r\n<html>ok</html>')
        wrapper = Mock(wraps=client); wrapper.connect = Mock()
        with patch.object(rf.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',80))]), patch.object(rf.socket,'socket',return_value=wrapper):
            self.assertEqual(rf.fetch_public_html(url), '<html>ok</html>')
        self.assertTrue(server.recv(4096).startswith(b'GET /products/caf%C3%A9?q=%C3%A9t%C3%A9&path=a%20b HTTP/1.1\r\n'))

    def test_real_http_response_connection_close_keeps_deadline_socket_usable(self):
        client, server = socket.socketpair()
        self.addCleanup(client.close); self.addCleanup(server.close)
        server.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/html\r\nContent-Length: 16\r\nConnection: close\r\n\r\n<html>ok</html> ')
        wrapper = Mock(wraps=client); wrapper.connect = Mock()
        with patch.object(rf.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',80))]), patch.object(rf.socket,'socket',return_value=wrapper):
            self.assertEqual(rf.fetch_public_html('http://example.com/product'), '<html>ok</html> ')

    def test_private_and_mixed_dns_never_connect(self):
        public = (socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))
        private = (socket.AF_INET,socket.SOCK_STREAM,6,'',('127.0.0.1',443))
        for addresses in [[private], [public, private]]:
            with patch.object(rf.socket,'getaddrinfo',return_value=addresses), patch.object(rf.socket,'socket') as create:
                with self.assertRaises(rf.FetchError): rf.fetch_public_html('https://example.com/product')
                create.assert_not_called()

    def test_dns_pin_https_sni_and_no_second_lookup(self):
        from email.message import Message
        headers=Message(); headers['Content-Type']='text/html; charset=utf-8'
        response=Mock(status=200, headers=headers); response.getheader.return_value='identity'
        response.read1.side_effect=[b'<html>Product</html>',b'']
        sock=Mock(); conn=Mock(); conn.getresponse.return_value=response
        context=Mock(); context.wrap_socket.return_value=sock
        with patch.object(rf.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',443))]) as dns, patch.object(rf.socket,'socket',return_value=sock), patch.object(rf.http.client,'HTTPConnection',return_value=conn), patch.object(rf.http.client,'HTTPResponse',return_value=response), patch.object(rf.ssl,'create_default_context',return_value=context):
            self.assertEqual(rf.fetch_public_html('https://example.com/product'), '<html>Product</html>')
            self.assertEqual(dns.call_count,1); sock.connect.assert_called_once_with(('93.184.216.34',443))
            context.wrap_socket.assert_called_once_with(sock,server_hostname='example.com')
            self.assertEqual(conn.sock,sock)

    def test_redirects_rechecked_and_bounded(self):
        with patch.object(rf,'_request',side_effect=[(302,'https://example.net/product',''),(200,'','<html>ok</html>')]) as request:
            self.assertEqual(rf.fetch_public_html('https://example.com/product'),'<html>ok</html>')
            self.assertEqual(request.call_args_list[1].args[0],'https://example.net/product')
        for redirect in ('http://example.com/insecure','http://localhost/private','file:///etc/passwd'):
            with patch.object(rf,'_request',return_value=(302,redirect,'')) as request:
                with self.assertRaises(rf.FetchError): rf.fetch_public_html('https://example.com/product')
                self.assertEqual(request.call_count,1)
        with patch.object(rf,'_request',return_value=(302,'/loop','')) as request:
            with self.assertRaises(rf.FetchError): rf.fetch_public_html('https://example.com/product')
            self.assertEqual(request.call_count,4)

    def test_binary_compressed_and_oversize_html_rejected(self):
        from email.message import Message
        for content_type, encoding, chunks in [('application/pdf','identity',[]),('text/html','gzip',[]),('text/html','identity',[b'x'*(rf.MAX_HTML+1)])]:
            headers=Message(); headers['Content-Type']=content_type
            response=Mock(status=200,headers=headers); response.getheader.return_value=encoding; response.read1.side_effect=chunks
            conn=Mock(); conn.getresponse.return_value=response
            with patch.object(rf.socket,'getaddrinfo',return_value=[(socket.AF_INET,socket.SOCK_STREAM,6,'',('93.184.216.34',80))]), patch.object(rf.socket,'socket'), patch.object(rf.http.client,'HTTPConnection',return_value=conn), patch.object(rf.http.client,'HTTPResponse',return_value=response):
                with self.assertRaises(rf.FetchError): rf.fetch_public_html('http://example.com/product')


if __name__ == '__main__': unittest.main()
