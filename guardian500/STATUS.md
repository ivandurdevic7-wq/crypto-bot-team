# Čuvar 500 — PAPER

- updated_at: 2026-10-27T10:16:19.493483+00:00
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
| 0xDA7D4AaCcbC139342CEe50968955075D64847777 | bsc | SKIP | max() arg is an empty sequence |
| 0xdc1392cfF00376e48F02c13125C289EDE23E6Daf | bsc | SKIP | pool younger than 24h |
| 0xFEE1e3eb419bD56b04Efbf14f809a3972660579B | bsc | SKIP | liquidity below $100k |
| FwtKA62k47DYe3jHmPNjspjVdc7PhipbqZjxTMfp81m6 | solana | SKIP | volume below $100k/day |
| G8KhLpeBPRhM6tMroEVC72H4Fv23KtwYzU1LZK6YE4rR | solana | SKIP | volume below $100k/day |
| GVEQKeEm2MeSVYQP3FM39xMnqqTdPaxLQaQrwbodpump | solana | SKIP | liquidity below $100k |
| GqzjCgpxZF1NEyk7wgWkGkgVYy6DXyobgy2TRT6vpump | solana | SKIP | 'liquidity' |
| GrtE7xGn3iBk93hhf1zz6i3Wbfv1uDd9unStGVhGpump | solana | SKIP | liquidity below $100k |
| HMTwjQPHbf82woGKMwDyPHAxgpwVj4boFQPMwk5Bpump | solana | SKIP | liquidity below $100k |
| J8kvdj2CMbbxL13jmTH3Ym4dYLfJEeiU1YfD9ynSpump | solana | SKIP | 'liquidity' |
| soCLGVqNFx63FcSwc89eTLABLXAg2tAoHJhDthz8ExZ | solana | SKIP | volume below $100k/day |

DEX: model naknade najmanje 0,4%, slippage 1% i mrežni trošak 0,25 EUR po strani. Nije izvediva swap ponuda. Uzorak tokena, ne cijela mreža. Nedostajući podaci = SKIP.


Virtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.
