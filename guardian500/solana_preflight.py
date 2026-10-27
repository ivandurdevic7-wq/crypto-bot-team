"""Read-only Solana route preflight. Quote != executable swap simulation.
PAPER ONLY: never signs, sends, or builds a real transaction.
"""
import json
import math
import os
import urllib.parse
import urllib.request

USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
BASE = "https://api.jup.ag/swap/v1/quote"


def validate_quote(data, input_mint, output_mint, in_amount, max_impact=0.01):
    if not isinstance(data, dict):
        raise ValueError("Jupiter response is not an object")
    if data.get("inputMint") != input_mint or data.get("outputMint") != output_mint:
        raise ValueError("Jupiter mint mismatch")
    def positive_int(v):
        if not isinstance(v, str) or not v.isdigit() or int(v) <= 0:
            raise ValueError("Jupiter amount missing or invalid")
        return int(v)
    if positive_int(data.get("inAmount")) != in_amount:
        raise ValueError("Jupiter input amount mismatch")
    out_amount = positive_int(data.get("outAmount"))
    threshold = positive_int(data.get("otherAmountThreshold"))
    if threshold > out_amount:
        raise ValueError("Jupiter output threshold invalid")
    routes = data.get("routePlan")
    if not isinstance(routes, list) or not routes:
        raise ValueError("Jupiter has no route")
    impact = float(data.get("priceImpactPct"))
    if not math.isfinite(impact) or not 0 <= impact <= max_impact:
        raise ValueError("Jupiter price impact too high or unavailable")
    return out_amount


def quote(mint_in, mint_out, amount, api_key):
    if not api_key:
        raise ValueError("JUPITER_API_KEY absent; fail closed")
    params = urllib.parse.urlencode({
        "inputMint": mint_in, "outputMint": mint_out, "amount": str(amount),
        "slippageBps": "100", "swapMode": "ExactIn",
    })
    req = urllib.request.Request(BASE + "?" + params, headers={
        "x-api-key": api_key, "User-Agent": "Cuvar500-PAPER-Preflight/1"
    })
    with urllib.request.urlopen(req, timeout=8) as response:
        if response.status != 200:
            raise ValueError("Jupiter quote unavailable")
        raw = response.read(131073)
        if len(raw) > 131072:
            raise ValueError("Jupiter quote too large")
    return validate_quote(json.loads(raw), mint_in, mint_out, amount)


def roundtrip_preflight(token_mint, token_decimals, usdc_amount=5_000_000):
    """Check USDC->token and token->USDC quotes; NEVER authorize an entry.
    Quote is not wallet-specific simulation. Future swap simulation integration
    must be separately reviewed before any new Solana DEX PAPER BUY.
    """
    key = os.getenv("JUPITER_API_KEY", "")
    if token_mint == USDC_MINT or not isinstance(token_decimals, int) or not 0 <= token_decimals <= 9:
        raise ValueError("Invalid token or decimals")
    acquired = quote(USDC_MINT, token_mint, usdc_amount, key)
    recovered = quote(token_mint, USDC_MINT, acquired, key)
    if recovered < usdc_amount * 0.95:
        raise ValueError("Excessive roundtrip quote loss")
    return {"status": "QUOTE_ONLY_NOT_SIMULATION", "usdc_in": usdc_amount,
            "usdc_back": recovered, "entry_allowed": False}
