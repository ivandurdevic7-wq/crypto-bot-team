# Čuvar 500 — PAPER

- updated_at: 2026-10-27T16:17:51.311318+00:00
- status: OK
- cash: 500.0
- equity_eur: 500.0
- pnl_eur: 0.0
- halted: False
- decisions: ['XBTEUR: WAIT', 'ETHEUR: WAIT', 'SOLEUR: WAIT']

## BNB Chain i Solana

{'bsc': 3, 'solana': 8}

| Token / adresa | Mreža | Odluka | Razlog |
|---|---|---|---|
| 0x51651ffcEe5a33a7a5E9CD8397D03c7F30E17777 | bsc | SKIP | pool younger than 12h |
| 0xc2af5a38362716fcd01503498bde858eb49790f8 | bsc | SKIP | no matching DEX pool |
| 0x0efb5FD2402A0967B92551d6AF54De148504A115 | bsc | SKIP | liquidity below $50k |
| 23wm1BzzW9pE3SyzBrD1z4v7Fq69cqoNjbCgaV4Cpump | solana | SKIP | 'liquidity' |
| 2ZbaN9Dkj5HPyYUeij82PcZgHJYZ8747Ca69qdcvCh5C | solana | SKIP | insufficient recent buys/sells |
| 38QPEZ8YYcF9wFpsg3FUJEP6PCS8dUDPkMfE1Hat4fit | solana | SKIP | 'liquidity' |
| 39jQot9cVECLm9zJVxyBZKmxitkzm6D4z2zmBiTyderp | solana | SKIP | 'liquidity' |
| 3SGJPK6m1shAU23hXdZrYXtiTfGviBeZLDNPqKH4kSPE | solana | SKIP | liquidity below $50k |
| 3cN6fwokMAYP1pyAn4MjjLL8mL9axyxhvjS9c6bzpump | solana | SKIP | 'liquidity' |
| 4ARnwMQZiJEzDuZ8r9As5kbs8QmaHi9rVWLx1ijNfair | solana | SKIP | 'liquidity' |
| 5MLP8C9gWiLt1q46VJ5PSEUiQM1ovdcqmnk7hzM5pump | solana | SKIP | 'liquidity' |

DEX: model naknade najmanje 0,4%, slippage 1% i mrežni trošak 0,25 EUR po strani. Nije izvediva swap ponuda. Uzorak tokena, ne cijela mreža. Nedostajući podaci = SKIP.


Virtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.
