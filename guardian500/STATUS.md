# Čuvar 500 — PAPER

- updated_at: 2026-10-27T10:51:17.166955+00:00
- status: OK
- cash: 500.0
- equity_eur: 500.0
- pnl_eur: 0.0
- halted: False
- decisions: ['XBTEUR: WAIT', 'ETHEUR: WAIT', 'SOLEUR: WAIT']

## BNB Chain i Solana

{'bsc': 4, 'solana': 8}

| Token / adresa | Mreža | Odluka | Razlog |
|---|---|---|---|
| 0x0efb5FD2402A0967B92551d6AF54De148504A115 | bsc | SKIP | liquidity below $100k |
| 0xDA7D4AaCcbC139342CEe50968955075D64847777 | bsc | SKIP | no matching DEX pool |
| 0xdc1392cfF00376e48F02c13125C289EDE23E6Daf | bsc | SKIP | pool younger than 24h |
| 0xFEE1e3eb419bD56b04Efbf14f809a3972660579B | bsc | SKIP | liquidity below $100k |
| 6zoj5GD7Pf5wrAnsqzWCE4oJG11v7mKEDueDJWYfpump | solana | SKIP | 'liquidity' |
| 7EqTnbCs8AfJXXtHPmyVvEKish47QzVafrncCpwRpump | solana | SKIP | liquidity below $100k |
| 7rkfsCSDbeTQPgNWaFUFdpkbsLX86kGWqR79pczpump | solana | SKIP | 'liquidity' |
| 81MXrQUZVKVhwBcP8pgZ543WK1eRSbnsFgnhzh6spump | solana | SKIP | 'priceUsd' |
| 97owM7j5K2ciCKjh1Efi8ix8Et9Tp7sjgnmLM2CHMamN | solana | SKIP | volume below $100k/day |
| 9gP2kCy3wA1ctvYWQk75guqXuHfrEomqydHLtcTCqiLa | solana | SKIP | volume below $100k/day |
| AjDibUH4NJxdhVvcxRU3dd1TBPcJksq4yJQVTTcvpump | solana | SKIP | 'priceUsd' |
| AkeAFeFKgyN687khQZfSUth7qNCnVoQJQu4uLRrQpump | solana | SKIP | 'liquidity' |

DEX: model naknade najmanje 0,4%, slippage 1% i mrežni trošak 0,25 EUR po strani. Nije izvediva swap ponuda. Uzorak tokena, ne cijela mreža. Nedostajući podaci = SKIP.


Virtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.
