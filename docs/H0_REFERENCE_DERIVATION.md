# H0 Referencia-Levezetés: Az Előzményfüggetlen Modell Rögzítése

**Szerző:** Instinct (Független elméleti partner)  
**Címzett:** Máté  
**Hivatkozott vak kalibráció:** [`results/pilot_characterization.json`](https://raw.githubusercontent.com/silentnoisehun/quantum-qubit-history-dependence/4ce92087944b001fb92b97777b39ed9385e5c0c9/results/pilot_characterization.json)  
**Hivatkozott szimulátor:** [`src/simulator.py`](https://raw.githubusercontent.com/silentnoisehun/quantum-qubit-history-dependence/4ce92087944b001fb92b97777b39ed9385e5c0c9/src/simulator.py)  
**Rögzített érték:** $L(\tau_0) = \mathbf{0.00}$  

---

## 1. Analitikus Levezetés a Vak Pilotból

A vak pilot empirikus mérése alapján:
- $T_1 = 219.39\ \mu\text{s}$
- $\Gamma = \frac{1}{T_1} = 4558.04\ \text{s}^{-1}$
- Mért kezdeti kontraszt: $S(0) = 0.9891$

Állandó, előzményfüggetlen (markovi) relaxáció esetén az $E$ ($|1\rangle$) és $G$ ($|0\rangle$) állapot-előkészítések különbsége:
$$S(t) = C \cdot \exp(-\Gamma t)$$

Az állandó kiolvasási eltolás a $P_E(t) - P_G(t)$ kivonásban, a $C$ amplitúdó pedig az $S(T)/S(0)$ hányadosban kiesik. Ez bizonyos reset- és állapot-előkészítési hibák mellett is érvényes, nem csupán tökéletes reset esetén.

A kalibrált $T = 220.0\ \mu\text{s}$ késleltetésnél:
$$\frac{S(T)}{S(0)} = \exp\left(-\frac{220.0}{219.39}\right) = 0.366862$$
$$S(T) \approx 0.9891 \times 0.366862 = 0.362864$$

Ha mindkét karra ($D$ és $I$) azonos relaxáció érvényes a reset után:
$$\Gamma_I = \Gamma_D \implies L(\tau_0) = \ln\left(\frac{\Gamma_I}{\Gamma_D}\right) = 0.00$$

---

## 2. A Modell Döntő Korlátja (Episztemikus Határ)

A környezet változatlansága ebben a levezetésben **FELTEVÉS**.

A pilot mérés közös $T_1$ értéke önmagában nem mondja meg, hogy a 64 darab $X$-kapuból álló periodikus meghajtás milyen mértékben változtatja meg a transmon lokális mikroszkopikus környezetét (TLS-telítődés, kvázirészecske-keltés, fűtés). Ehhez hiányzik:
1. A meghajtásra adott környezeti rátaválasz nagysága ($\Delta \Gamma$).
2. A környezet relaxációs visszaállási ideje ($\tau_{\text{mem}}$).

Ezen mikroszkopikus csatolási paraméterek nélkül a valódi QPU-n várható hatásméret nem vezethető le egyértelműen.

### Összehasonlítás a pozitív becslésekkel:
Ha az $I$-kar $T_1$-e $219.39\ \mu\text{s}$:
- Egy $+0.08$-as érték $T_{1,D} \approx 237.67\ \mu\text{s}$-ot jelentene (kb. $7.69\%$-kal kisebb lecsengési ráta a hajtott karban).
- Ez azonban feltételes átszámítás, nem cáfolat és nem önálló bizonyíték mellette.

---

## 3. Szimulációs Szenzitivitás és Aszimmetrikus Szivárgási Figyelmeztetés

A numerikus szimulációkban (`src/simulator.py`) a lassulás mértéke mesterségesen, előre beállított bemenet:
- A pipeline a beadott $7.5\%$-os rátacsökkenést 500-ból 456-szor felismerte ($91.2\%$-os statisztikai erő). Ez az elemző mérési érzékenységét méri, nem a hardver várható hatásának levezetése.

### Kritikus szivárgási figyelmeztetés:
Az aszimmetrikus szivárgási tesztben ($|2\rangle \to |1\rangle \to |0\rangle$ kaszkád játékmodell) **500 futtatásból 23 alkalommal (4.6%) hamis lassulás ($L > 0$) adódott**.
Ez egy játékmodellben feltárt elemzési sérülékenység (nem hardveres szivárgás bizonyítéka), amely előre figyelmeztetett arra, hogy az aszimmetrikus szivárgás képes enyhe látszólagos lassulást generálni az $1\%$-os szinten.

---

## 4. Összegzés és Kapcsolódás a Konfirmatív Mérési Eredményekhez

> *"Vállalom a 0,00-t, de pontosan így: az előzményfüggetlen modellből levezetett előrejelzésem. Nem állítom, hogy ezzel már kiszámoltam a valódi környezet válaszát is. Ezt a hiányt nem fedem el egy választott pozitív számmal."*

### Konvergencia a valós mérési adatokkal:
A valós Heron QPU mérés (`ibm_marrakesh`, 8 blokk) pontosan tükrözi ezt a kettősséget:
1. **A relaxációs ráta ($L$):** Mind a 6 blokkos ($\bar{L} = +0.0360$, $p = 0.16$), mind a 8 blokkos ($\bar{L} = +0.0220$, $p = 0.29$) eredmény statisztikailag nem döntő; nem cáfolja meg az Instinct által levezetett $0.00$-s értéket, de nem zárja ki a $+0.10$-es értéket sem.
2. **A $G$-előkészítés utáni kiolvasási kontraszt ($S5$):** $P_G^D(0) - P_G^I(0) = +0.00425$ ($+0.425$ százalékpont, $p = 0.00051$). Ez a mérés megbízhatóan kimutatja a két kar közötti kiolvasási kontrasztot a $G$-előkészítés után. Ebből önmagában nem következik romló reset vagy ötszörös valódi gerjesztett maradékpopuláció: a gerjesztés, szivárgás és kiolvasási torzítás ebben a mérésben nincs szétválasztva, így a mögöttes fizikai ok nyitott kérdés marad.
