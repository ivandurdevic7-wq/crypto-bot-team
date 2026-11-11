"""Optional live Jupiter quote smoke test. Never executes swaps.
Requires JUPITER_API_KEY from GitHub Actions secrets; never print the key.
This is a diagnostics-only probe for SOL/USDC, not an entry authorization.
"""
import json
import os
import sys
from solana_preflight import quote, USDC_MINT

SOL_MINT = "So11111111111111111111111111111111111111112"

def main():
    key = os.environ.get("JUPITER_API_KEY", "")
    if not key:
        print(json.dumps({"status": "SKIP_NO_API_KEY", "entry_allowed": False}))
        return 0
    try:
        out = quote(USDC_MINT, SOL_MINT, 1_000_000, key)
        if out <= 0:
            raise ValueError("no output")
    except Exception as error:
        print(json.dumps({"status": "API_CHECK_FAILED", "type": type(error).__name__,
                          "entry_allowed": False}))
        return 1
    print(json.dumps({"status": "QUOTE_API_OK_NOT_SWAP_SIMULATION",
                      "entry_allowed": False}))
    return 0

if __name__ == "__main__":
    sys.exit(main())
