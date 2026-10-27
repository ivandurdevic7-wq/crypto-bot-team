"""Fail-closed Jupiter quote checks; no network requests."""
import unittest
from solana_preflight import validate_quote, roundtrip_preflight, USDC_MINT

TOKEN = "So11111111111111111111111111111111111111112"

class SolanaPreflightTests(unittest.TestCase):
    def data(self):
        return {"inputMint": USDC_MINT, "outputMint": TOKEN,
                "inAmount": "5000000", "outAmount": "25000000",
                "router": "metis", "transaction": None}

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

    def test_wrong_amount(self):
        with self.assertRaises(ValueError): validate_quote(self.data(), USDC_MINT, TOKEN, 1)

    def test_no_api_key_fails_closed(self):
        from unittest.mock import patch
        with patch.dict("os.environ", {"JUPITER_API_KEY": ""}):
            with self.assertRaises(ValueError): roundtrip_preflight(TOKEN, 9)
