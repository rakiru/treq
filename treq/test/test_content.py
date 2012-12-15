import mock

from twisted.trial.unittest import TestCase
from twisted.python.failure import Failure

from twisted.web.http_headers import Headers
from twisted.web.client import ResponseDone, ResponseFailed

from treq import collect, content, json_content, text_content


class ContentTests(TestCase):
    def setUp(self):
        self.response = mock.Mock()
        self.protocol = None

        def deliverBody(protocol):
            self.protocol = protocol

        self.response.deliverBody.side_effect = deliverBody

    def successResultOf(self, d, expected):
        results = []
        d.addBoth(results.append)

        if isinstance(results[0], Failure):
            results[0].raiseException()

        self.assertEqual(results[0], expected)

    def failureResultOf(self, d, errorType):
        results = []
        d.addBoth(results.append)

        if not isinstance(results[0], Failure):
            self.fail("Expected {0} got {1}.".format(errorType, results[0]))

        self.assertTrue(results[0].check(errorType))

    def test_collect(self):
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived('{')
        self.protocol.dataReceived('"msg": "hell')
        self.protocol.dataReceived('o"}')

        self.protocol.connectionLost(Failure(ResponseDone()))

        self.successResultOf(d, None)

        self.assertEqual(data, ['{', '"msg": "hell', 'o"}'])

    def test_collect_failure(self):
        data = []

        d = collect(self.response, data.append)

        self.protocol.dataReceived('foo')

        self.protocol.connectionLost(Failure(ResponseFailed("test failure")))

        self.failureResultOf(d, ResponseFailed)

        self.assertEqual(data, ['foo'])

    def test_collect_0_length(self):
        self.response.length = 0

        d = collect(
            self.response,
            lambda d: self.fail("Unexpectedly called with: {0}".format(d)))

        self.successResultOf(d, None)

    def test_content(self):
        d = content(self.response)

        self.protocol.dataReceived('foo')
        self.protocol.dataReceived('bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.successResultOf(d, 'foobar')

    def test_content_cached(self):
        d1 = content(self.response)

        self.protocol.dataReceived('foo')
        self.protocol.dataReceived('bar')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.successResultOf(d1, 'foobar')

        def _fail_deliverBody(protocol):
            self.fail("deliverBody unexpectedly called.")

        self.response.deliverBody.side_effect = _fail_deliverBody

        d2 = content(self.response)

        self.successResultOf(d2, 'foobar')

        self.assertNotIdentical(d1, d2)

    def test_json_content(self):
        d = json_content(self.response)

        self.protocol.dataReceived('{"msg":"hello!"}')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.successResultOf(d, {'msg': 'hello!'})

    def test_text_content(self):
        self.response.headers = Headers(
            {'Content-Type': ['text/plain; charset=utf-8']})

        d = text_content(self.response)

        self.protocol.dataReceived('\xe2\x98\x83')
        self.protocol.connectionLost(Failure(ResponseDone()))

        self.successResultOf(d, u'\u2603')
