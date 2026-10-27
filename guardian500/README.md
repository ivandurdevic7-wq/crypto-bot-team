# Čuvar 500
Autonomna PAPER simulacija, početno 500 EUR. Nema privatnih ključeva, računa niti funkcije slanja stvarnih naloga. Nova strategija nije dokazano profitabilna.

BTC/EUR, ETH/EUR, SOL/EUR: zatvorena satna svijeća mora probiti prethodnih 20 maksimuma, uz SMA20 > SMA50. Izlaz ispod SMA20, stop 4%, trailing 5%. Najviše 2 pozicije, svaka do 20% kapitala, uz ciljani rizik 0,75% po poziciji. Dnevni pad 3% obustavlja ulaze i likvidira virtualne pozicije pri sljedećoj valjanoj provjeri; pad 8% od vrha trajno zaustavlja ulaze. Limiti nisu jamstvo maksimalnog gubitka.

Model troška: 0,4% po strani + 0,1% slippage + stvarni bid/ask spread. Nisu potvrđene naknade korisničkog računa. Knjiga naloga služi kao filter, ne kao puna simulacija izvršenja. Stopovi se izvršavaju po sljedećoj dostupnoj cijeni, nikad retroaktivno po željenoj cijeni.

Kraken public API: svježina trgovanja do 5 minuta, satne svijeće bez rupa, provjera vremena servera i statusa burze. Nedostatak podataka zamrzava odluke za cijeli ciklus; postojeće pozicije ostaju izložene. STATUS.md prikazuje vrijeme posljednje uspješne valuacije. Dnevnik je state.json.

Pokretanje: `python guardian500/bot.py`. Testovi: `python -m unittest discover -s guardian500 -p 'test_*.py'`.

GitHub Actions raspored svakih 15 minuta radi bez otvorenog preglednika, ali može kasniti ili biti preskočen. Javni repozitorij znači javne virtualne rezultate. Zaustavi workflow u GitHub Actions za potpuno gašenje. Ne briši state.json jer bi to resetiralo račun.

Izvori: https://docs.kraken.com/api/docs/rest-api/get-ohlc-data/ i https://support.kraken.com/articles/360000919986-public-endpoint-examples-you-can-try-them-directly-in-a-web-browser-

## V2: BNB Chain + Solana
Zajednički state.json i istih početnih 500 EUR za burzovne parove i DEX tokene. Najviše dvije ukupne pozicije. BNB izvori ograničeni na PancakeSwap; Solana obuhvaća DEX-ove koje vraća DEX Screener. Najviše 8 kandidata po mreži/ciklusu uz obavezno osvježavanje otvorenih pozicija; rotacija kandidata i zadržavanje uspješno provjerenih tokena do 24 sata. Ovo nije indeks svih novih tokena i ne prati Telegram.

Ulaz: bazen star najmanje 24h, likvidnost najmanje 100.000 USD, dnevni volumen najmanje 100.000 USD i najmanje dvije kupnje/prodaje u posljednjih 5 minuta. GoPlus mora vratiti sve tražene podatke. Nepoznati ili rizični podaci blokiraju kupnju. BNB provjera uključuje honeypot, poreze, proxy i administrativne ovlasti; Solana uključuje mint/freeze, transfer hook i naknade. Obje mreže: top10 udio <=35%, pojedinačni <=10% (konzervativno uključuje bazene). Potrebna je potvrda odabranog bazena i njegove naknade od GoPlusa. Ne potvrđujemo zaključavanje LP-a niti jamčimo mogućnost prodaje: nedostaje simulacija swapa za konkretnu adresu novčanika. GoPlus je vanjska procjena, ne sigurnosno jamstvo.

Signal zahtijeva dvije opažene cijene istog bazena u razmaku 10–60 minuta, rast 0,5–8%, satni rast 1–15% i dnevnu promjenu -5 do +50%. Promotivni profil ili plaćeni boost nisu signal za kupnju. DEX trošak modela: stvarna prijavljena naknada bazena ili najmanje 0,4%, plus 1% slippage i 0,25 EUR mrežnog troška po strani. Samo tokeni bez prijavljenog poreza. Te pretpostavke nisu izvršiva ponuda ni stvarni gas. USD cijene pretvaraju se aktualnim EUR/USD parom na Krakenu.

Pozicija do 25 EUR, ciljani rizik 0,5% portfelja uključujući model troška, stop 8%, trailing 10%. Globalna pravila pada 3%/8% ostaju. Ako nedostaje cijena ili sigurnosna provjera postojeće pozicije, cijeli ciklus trgovanja staje: nema izmišljene prodaje ni dobiti. Dnevnik zadržava posljednju uspješnu valuaciju s vremenom.

HTTP vrijeme/cache i aktivnost u zadnjih 5 minuta služe za odbacivanje zastarjelih odgovora; DEX Screener ne daje izričit timestamp same kotacije. To nije tick-feed ni potpuna potvrda svježine svake cijene. Nedostajući izvori prikazuju se u source_errors/dex_scan.errors.

Dokumentacija: https://docs.dexscreener.com/api/reference ; https://docs.gopluslabs.io/reference/response-details ; https://docs.gopluslabs.io/reference/response-detail-1

## V3: strože provjere i nadzor
BNB ulazi zahtijevaju uspješnu Honeypot.is simulaciju kupnje/prodaje za točan token, chain 56 i bazen, nulte prijavljene poreze, riskLevel <20 i dovoljan prijavljeni limit veličine ako postoji. To je simulacija pružatelja, ne simulacija konkretnog korisničkog novčanika. https://docs.honeypot.is/ishoneypot

Solana simulacija nije integrirana: mreža se i dalje skenira, ali novi DEX ulazi ostaju blokirani. Nepodržane provjere nisu PASS.

LP: najmanje 90% ukupne ponude LP-a mora biti spaljeno na prepoznatoj BNB burn adresi ili zaključano najmanje 7 dana, prema količini i vremenu zaključavanja. Podržani su samo standardni/UniV2 bazeni s nedvosmislenim pripisivanjem LP podataka jednom bazenu. Ako GoPlus vrati više bazena, agregirani LP podaci nisu dokaz za odabrani bazen: SKIP. V3/concentrated liquidity i nedostajući podaci su nepotvrđeni. Nadolazeće otključavanje prikazuje se u next_unlock kada je dostupno. Konzervativni kriteriji mogu blokirati većinu tokena.

Pad opažene USD likvidnosti >25% kroz najviše 2 sata blokira ulaz i bilježi upozorenje; takav pad nije dokaz povlačenja LP-a jer na USD vrijednost utječe cijena. Bot ne šalje vanjske obavijesti. HTML označava starost posljednje uspješne procjene, pokušaja i DEX provjere, s upozorenjem nakon 30 min i kritičnim nakon 60 min. Učitavanje GitHub datoteke nije dokaz da je bot upravo radio.
