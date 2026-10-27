# Čuvar 500 — PAPER

- updated_at: 2026-10-27T15:44:31.330583+00:00
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
| 0x0efb5FD2402A0967B92551d6AF54De148504A115 | bsc | SKIP | liquidity below $50k |
| 0x51651ffcEe5a33a7a5E9CD8397D03c7F30E17777 | bsc | SKIP | pool younger than 12h |
| 0xa5999cb9871fb8bd9fef9a3dec7d48fcd8a10fed | bsc | SKIP | no matching DEX pool |
| 0xDb1160d96885993a69BD9cb149EbfF4D4A437777 | bsc | SKIP | no matching DEX pool |
| 61uUYv7jRhZkpNuG6DCFppsSaFBea5TP7fLuRzQ4pump | solana | SKIP | liquidity below $50k |
| 6ueGm9qsdDY1vFf2M6v6whVbYY2qXU6RwrqJ6ZPG9C3q | solana | SKIP | volume below $30k/day |
| 6xKicXmEgJEZ8YeWUBKyh8iSU1kJ9fMEUbZJjQfF7dd9 | solana | SKIP | volume below $30k/day |
| 7wKNhej9P1trJwuXKbFooD7snv6h6meLr14qoEg8pump | solana | SKIP | liquidity below $50k |
| 81Y1jv7kDNQotwTXT4CkpZ2gNE2TedVTLFYnEW1ppump | solana | SKIP | 'liquidity' |
| 8ULZXvZMXcrpnwQo87aQVMNKf7HzgMQSEwr3ZUQKpump | solana | SKIP | liquidity below $50k |
| 8qJ7GkF9PzEf1tNWS9evtWqKDXv8DVDcX3m9Sjajpump | solana | SKIP | 'liquidity' |
| 97owM7j5K2ciCKjh1Efi8ix8Et9Tp7sjgnmLM2CHMamN | solana | SKIP | volume below $30k/day |

DEX: model naknade najmanje 0,4%, slippage 1% i mrežni trošak 0,25 EUR po strani. Nije izvediva swap ponuda. Uzorak tokena, ne cijela mreža. Nedostajući podaci = SKIP.


Virtualni rezultat; nije stvarna zarada. Naknada modela 0,4% po strani + 0,1% slippage i bid/ask spread. Stop se provjerava samo pri pokretanju, pa gubitak može prijeći limit.
