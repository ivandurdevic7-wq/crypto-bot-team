# Čuvar 500
Autonomna PAPER simulacija, početno 500 EUR. Nema privatnih ključeva, računa niti funkcije slanja stvarnih naloga. Nova strategija nije dokazano profitabilna.

BTC/EUR, ETH/EUR, SOL/EUR: zatvorena satna svijeća mora probiti prethodnih 20 maksimuma, uz SMA20 > SMA50. Izlaz ispod SMA20, stop 4%, trailing 5%. Najviše 2 pozicije, svaka do 20% kapitala, uz ciljani rizik 0,75% po poziciji. Dnevni pad 3% obustavlja ulaze i likvidira virtualne pozicije pri sljedećoj valjanoj provjeri; pad 8% od vrha trajno zaustavlja ulaze. Limiti nisu jamstvo maksimalnog gubitka.

Model troška: 0,4% po strani + 0,1% slippage + stvarni bid/ask spread. Nisu potvrđene naknade korisničkog računa. Knjiga naloga služi kao filter, ne kao puna simulacija izvršenja. Stopovi se izvršavaju po sljedećoj dostupnoj cijeni, nikad retroaktivno po željenoj cijeni.

Kraken public API: svježina trgovanja do 5 minuta, satne svijeće bez rupa, provjera vremena servera i statusa burze. Nedostatak podataka zamrzava odluke za cijeli ciklus; postojeće pozicije ostaju izložene. STATUS.md prikazuje vrijeme posljednje uspješne valuacije. Dnevnik je state.json.

Pokretanje: `python guardian500/bot.py`. Testovi: `python -m unittest discover -s guardian500 -p 'test_*.py'`.

GitHub Actions raspored svakih 15 minuta radi bez otvorenog preglednika, ali može kasniti ili biti preskočen. Javni repozitorij znači javne virtualne rezultate. Zaustavi workflow u GitHub Actions za potpuno gašenje. Ne briši state.json jer bi to resetiralo račun.

Izvori: https://docs.kraken.com/api/docs/rest-api/get-ohlc-data/ i https://support.kraken.com/articles/360000919986-public-endpoint-examples-you-can-try-them-directly-in-a-web-browser-
