"""Fail-closed Jupiter quote checks; no network requests."""
import unittest
import json
from unittest.mock import patch
import solana_preflight
from solana_preflight import validate_quote, roundtrip_preflight, USDC_MINT

TOKEN = "So11111111111111111111111111111111111111112"

class SolanaPreflightTests(unittest.TestCase):
    def data(self):
        return {"inputMint": USDC_MINT, "outputMint": TOKEN,
                "inAmount": "5000000", "outAmount": "25000000",
                "router": "metis", "transaction": None, "feeBps": 10}

    def test_valid_quote(self):
        self.assertEqual(validate_quote(self.data(), USDC_MINT, TOKEN, 5000000), 25000000)

    def test_mint_mismatch(self):
        d=self.data(); d["outputMint"]="wrong"
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_missing_router(self):
        d=self.data(); d["router"]=None
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_transaction_is_refused(self):
        d=self.data(); d["transaction"]="base64"
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_excessive_fee(self):
        d=self.data(); d["feeBps"]=250
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_missing_transaction_field(self):
        d=self.data(); del d["transaction"]
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_error_response(self):
        d=self.data(); d["errorCode"]=6001
        with self.assertRaises(ValueError): validate_quote(d, USDC_MINT, TOKEN, 5000000)

    def test_wrong_amount(self):
        with self.assertRaises(ValueError): validate_quote(self.data(), USDC_MINT, TOKEN, 1)

    def test_no_api_key_fails_closed(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"JUPITER_API_KEY": ""}):
            with self.assertRaises(ValueError): roundtrip_preflight(TOKEN, 9)

    def test_quote_is_read_only_get(self):
        requests = []
        payload = json.dumps(self.data()).encode()
        class FakeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, length): return payload
        def fake_open(request, timeout):
            requests.append(request)
            return FakeResponse()
        with patch.object(solana_preflight.urllib.request, "urlopen", side_effect=fake_open):
            received = solana_preflight.quote(USDC_MINT, TOKEN, 5000000, "unit-test-key")
        self.assertEqual(received, 25000000)
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].get_method(), "GET")
        self.assertNotIn("taker=", requests[0].full_url)
        self.assertIn("/swap/v2/order?", requests[0].full_url)
