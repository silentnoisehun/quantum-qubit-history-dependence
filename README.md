# Qvantum qbit history depence
### Quantum Qubit History Dependence — "A Qubit Gumija" Kísérlet

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://python.org)
[![Qiskit: 2.x](https://img.shields.io/badge/Qiskit-2.4.2-purple.svg)](https://qiskit.org)

Előregisztrált kvantum hardver kísérlet annak vizsgálatára, hogy a transzmon qubit reset előtti periodikus meghajtása lassítja-e a reset utáni $|1\rangle$ állapot lecsengését egy azonos idejű üresjárati várakozáshoz képest.

---

## 1. A Hipotézis és Referenciák

- **Máté irányhipotézise (H1):**  
  A reset előtti periodikus meghajtás után a qubit lassabban veszíti el az $|1\rangle$ populációt, mint az azonos hosszú várakozás után.  
  A relatív rátaváltozás logaritmusa:
  $$L(\tau) = \ln\left(\frac{\Gamma_I}{\Gamma_D}\right)$$
  $L(\tau_0) > 0$, és a hatás a meghajtás vége és a reset között eltelt várakozási idő ($\tau$) növekedésével csökken.

- **Előzményfüggetlen referencia (H0):**  
  Ideális reset és markovi környezet esetén a qubit kimenete független a reset előtti dinamikától: minden $\tau$-ra $L(\tau) = 0$.

- **Ismert mechanizmusok (M):**  
  A reset kizárólag a qubit látható állapotát állítja vissza, a környezeti szabadsági fokokat (TLS-telítettség, kvázirészecske-dinamika, chip-melegedés, $|2\rangle$ állapot szivárgási maradéka) nem feltétlenül. Egy eltérés elsősorban ezen mechanizmusok nyoma, nem új fizika.

---

## 2. Elméleti Korrekciók és Hivatkozások (v0.1)

A reggeli elméleti vázlat felülvizsgálata és szigorítása:

1. **Nem minden ismert mechanizmus gyorsítja a lecsengést:**  
   Gustavsson és munkatársai igazolták, hogy egy meghajtó impulzussorozattal a kvázirészecskék sűrűsége ~70%-kal csökkenthető, ami a $T_1$ háromszoros növekedését eredményezi ([Science 354, 1573, 2016](https://arxiv.org/abs/1612.08462)). Ezen felül a $|2\rangle$ állapot szivárgásából eredő $2 \to 1 \to 0$ kaszkád szintén lassabb látszólagos lecsengést okozhat a $P(1)$ görbén.
2. **TLS ingadozás mint sodródási komponens:**  
   Klimov és munkatársai kimutatták, hogy a $T_1$ akár egy nagyságrendet is ingadozhat 15 perces időskálán a kétállapotú hibák (TLS) spektrális diffúziója miatt ([arXiv:1809.01043](https://arxiv.org/abs/1809.01043)). Emiatt a mérések blokkon belüli lövésszintű összefésülést (interleaving) és szigorú sodródás-kontrollt követelnek.
3. **Hardveres vezérlés korlátai:**  
   Az IBM 2025. február 3-án kivezette a pulzusszintű vezérlést (OpenPulse). A virtuális RZ kapuk nem visznek be energiát, így nem használhatók energia-kontrollként. Helyette szigorú kapuszintű kontrollok futnak:
   - $D$ (meghajtás): egyenletesen elosztott $N$ db $X$ kapu $q$-n.
   - $I$ (üresjárati kontroll): azonos idejű delay kapuk nélkül $q$-n.
   - $Nb$ (szomszéd meghajtás): $N$ db $X$ a szomszéd $q'$ qubiten (áthallás és melegedés kontroll).
   - $D_{\text{fast}}$ (gyors párok): $N/2$ db szoros $X\text{--}X$ pár (impulzusszám vs. gerjesztési idő elválasztása).

---

## 3. Repozitórium Struktúra

```
quantum-qubit-history-dependence/
├── docs/                   # Specifikációk és protokoll dokumentumok
│   └── PREREGISTRATION_v0.1.md
├── prereg/                 # Lefagyasztott előregisztráció és manifest hash-ek
│   ├── PREDICTIONS.md
│   └── manifest_audit.json
├── src/                    # Kísérleti és fordítási kódok
│   ├── circuit_builder.py  # Áramkör-generátor (barrier-védett, fail-closed)
│   ├── audit_transpiler.py # Fordítási és ISA ellenőrző
│   ├── simulator.py        # Validációs szimulátor (null-teszt, MDE, szivárgás)
│   └── analysis.py         # Kétoldali statisztikai elemző (alpha = 0.01)
├── tests/                  # Egységtesztek és szimulációs tesztek
├── data/                   # Kalibrációs és mérési adatok (pilot, kampány)
└── results/                # Elemzési jelentések és ábrák
```

---

## 4. Fordítási Audit és Biztonsági Szabályok (Fail-Closed)

- `optimization_level = 0`, explicit `initial_layout`, barrier minden kondicionáló kapu között.
- Dinamikus dekoherencia (DD) és mérési twirling szigorúan kikapcsolva.
- QPU-beküldés kizárólag Máté előzetes írásbeli jóváhagyásával, rögzített manifest hash és audit után.
