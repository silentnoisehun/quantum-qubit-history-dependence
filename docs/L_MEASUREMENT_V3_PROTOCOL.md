# L-MÉRÉS v3 Pre-regisztrációs Jegyzőkönyv: 0.00 kontra +0.08

**Dokumentum verzió:** `v3.0.0-frozen-prereg`  
**Dátum (UTC):** 2026-11-22  
**Státusz:** **FAGYASZTOTT TERV ÉS SZIMULÁCIÓS AUDIT (INDÍTÁSRA VÁR)**  
**Backend:** `ibm_marrakesh` (Heron r2, 156-qubit QPU)  
**Qubitpár:** Elsődleges $q=21$, Szomszéd $q'=20$  
**Cél:** $L = \ln(\Gamma_I / \Gamma_D)$ pontjóslatok rigorózus szétválasztása az elméleti referencia ($L = 0.00$) és a hajtott jóslat ($L = +0.08$) között.

---

## 1. Célkitűzés és Episztemikus Keret

A mérés célja a relaxációs ráták logaritmikus hányadosának meghatározása a legkisebb holtidőnél ($\tau_0 = 8\text{ ns}$):
$$L(\tau_0) = \ln\left(\frac{\Gamma_I}{\Gamma_D}\right)$$
- **Instinct elméleti Markov-referenciája:** $L = 0.00$ (a 64 kapus hajtás nem változtatja meg a qubit relaxációs környezetét a reset után).
- **Máté elméleti jóslata:** $L = +0.08$ ($\approx 7.69\%$-os rátacsökkenés, $T_{1,D} \approx 238\ \mu\text{s}$ a kalibrált $T_{1,I} \approx 219.4\ \mu\text{s}$ mellett).
- *Megjegyzés:* A korábbi repóban szereplő feltáró $+0.10$-es sáv ettől külön marad.
- *Episztemikus határ:* A mérés önmagában a makroszkopikus relaxációs rátát és annak kontrasztját méri, nem azonosít önálló mikroszkopikus mechanizmust (pl. TLS dinamika, fononcsatolás vagy szivárgás).

---

## 2. Hardver és Áramköri Paraméterek

| Paraméter | Érték | Leírás / Megjegyzés |
|---|---|---|
| **Backend** | `ibm_marrakesh` | IBM Quantum Heron r2 processzor |
| **Qubitpár** | $q=21$ (aktív), $q'=20$ (szomszéd) | Csatolt fizikai transzmon pár |
| **Időzítési egység ($dt$)** | $4.0\text{ ns}$ | Mintavételezési ráta |
| **$X$-kapu idő ($t_X$)** | $36.0\text{ ns}$ ($9\ dt$) | Egyqubites forgatás |
| **Kondicionálási idő ($T_c$)** | $16.128\ \mu\text{s}$ ($4032\ dt$) | $64$ résre osztott szekvencia |
| **Kondicionálási impulzusok ($N$)** | $64\ X$-kapu | $D$ karon $q21$-en, $I$ karon várakozás |
| **Legkisebb holtidő ($\tau_0$)** | $8.0\text{ ns}$ ($2\ dt$) | Közvetlen reset előtti várakozás |
| **Maximális holtidő ($\tau_{\max}$)** | $64.0\ \mu\text{s}$ ($16000\ dt$) | Időzítés-kiegyenlítő pre-reset padding |
| **Lecsengési idő ($T$)** | $220.0\ \mu\text{s}$ ($55000\ dt$) | Kalibrált pilot $T_1 = 219.39\ \mu\text{s}$ alapján |
| **Modellellenőrzési idő ($2T$)** | $440.0\ \mu\text{s}$ ($110000\ dt$) | Exponencialitás vizsgálata |
| **Ismétlési késleltetés (`rep_delay`)** | $250.0\ \mu\text{s}$ | $> 1.38 \times T_1$ termalizáció |
| **Inicializálás (`init_qubits`)** | `True` | Hardveres aktív reset minden lövés előtt |
| **Optimalizálás & Hibacsökkentés** | `optimization_level=0` | DD = KI, Twirling = KI (fail-closed) |

---

## 3. Blokkszerkezet és Lövéseloszlás

Minden mérési alkalom egyetlen zárt blokkból áll:

### A. Mag Áramkörök (12 áramkör / blokk, 10 000 lövés)
- **Hajtott kar ($D$):**
  - $G(0)$: 500 lövés
  - $E(0)$: 500 lövés
  - $G(T)$: 500 lövés
  - $E(T)$: 1500 lövés (kiemelt statisztikai pontosság a relaxált végponton)
  - $G(2T)$: 1000 lövés (modellellenőrzés)
  - $E(2T)$: 1000 lövés (modellellenőrzés)
  *Részösszeg $D$: 5 000 lövés.*
- **Üresjárati kar ($I$):**
  - $G(0)$: 500 lövés
  - $E(0)$: 500 lövés
  - $G(T)$: 500 lövés
  - $E(T)$: 1500 lövés
  - $G(2T)$: 1000 lövés
  - $E(2T)$: 1000 lövés
  *Részösszeg $I$: 5 000 lövés.*

### B. Opcionális Leíró Kontroll: $D_{\text{fast}}$ (+4 áramkör, +3 000 lövés)
- $G(0)$: 500 lövés, $E(0)$: 500 lövés, $G(T)$: 500 lövés, $E(T)$: 1500 lövés.
- *Döntés a bevonásról:* A fagyasztott terv mindkét konfigurációt számszerűsíti. A magkísérlet 10 000 lövés/blokk, a kibővített 13 000 lövés/blokk.

### C. Áramkörök Kanonikus Hash-jegyzéke (SHA256)
| Címke | Kar | Előkészítés | Idő $t$ | Lövésszám | Mélység | SHA256 Részlet |
|---|---|---|---|---|---|---|
| `D_tau_8ns_G_t0` | D | G | $0$ | 500 | 197 | `ca190a27bcea68e4...` |
| `D_tau_8ns_E_t0` | D | E | $0$ | 500 | 197 | `d5a3108d50db2064...` |
| `D_tau_8ns_G_tT` | D | G | $T$ | 500 | 198 | `f7f51e59def2da76...` |
| `D_tau_8ns_E_tT` | D | E | $T$ | 1500 | 198 | `fd6de0e66feeb9c3...` |
| `D_tau_8ns_G_t2T_mc` | D | G | $2T$ | 1000 | 198 | `e7afc6d473e11971...` |
| `D_tau_8ns_E_t2T_mc` | D | E | $2T$ | 1000 | 198 | `deef682ec134b62f...` |
| `I_tau_8ns_G_t0` | I | G | $0$ | 500 | 6 | `6a3cb569ed7ff734...` |
| `I_tau_8ns_E_t0` | I | E | $0$ | 500 | 6 | `700a66cf1b88e2c9...` |
| `I_tau_8ns_G_tT` | I | G | $T$ | 500 | 7 | `07a6c6b219c97898...` |
| `I_tau_8ns_E_tT` | I | E | $T$ | 1500 | 7 | `98e7c81664c0c7a9...` |
| `I_tau_8ns_G_t2T_mc` | I | G | $2T$ | 1000 | 7 | `c99e6ea3317ec6d1...` |
| `I_tau_8ns_E_t2T_mc` | I | E | $2T$ | 1000 | 7 | `0acef6f96c085f09...` |

---

## 4. Ütemezés és Carry-over Transzparencia

1. **16 Elkülönített Mérési Alkalom:**
   - 16 időben szeparált alkalom, alkalmanként 1 blokk.
   - Időköz: $\Delta t = 60\text{ perc}$ (vagy $90\text{ perc}$ a teljes diurnal drift átfogására).
   - Nem egyetlen gyors beküldési köteg, hanem diszkrét, független QPU jobok.
2. **Blokkon Belüli Véletlen Áramkörsorrend:**
   - Minden alkalomhoz determinisztikus pszeudo-véletlen seed rögzítve (`seed = 20261122 + session_id`).
   - A sorrend átrendezése kiküszöböli a hardveres drift szisztematikus áttolódását az áramkörök között.
3. **Inicializálás és Carry-over Elemzés:**
   - Minden egyes áramkör előtt és az áramkörök minden egyes lövésénél lefut a hardveres aktív reset (`init_qubits=True`).
   - A lövések közötti termalizációs idő $250.0\ \mu\text{s}$ (`rep_delay`), amihez hozzájön a pre-reset conditioning és padding időtartama ($80.128\ \mu\text{s}$). Ez összesen $> 330\ \mu\text{s}$ holtidő ($> 1.8 \times T_1$).
   - Az áramkörök közötti lehetséges carry-over így kizárólag a legelső lövésnél léphetne fel elméletileg, de a hardveres aktív reset és a $250\ \mu\text{s}$ késleltetés mellett ennek valószínűsége $< 0.2\%$, és a véletlenszerű sorrend miatt nem tud irányított torzítást okozni.

---

## 5. Előre Rögzített Elemzés és Döntési Szabály

### A. Kontraszt és Ráta Számítása
$$S(t) = P_E(t) - P_G(t)$$
$$\Gamma = -\frac{1}{T} \ln\left[\frac{S(T)}{S(0)}\right]$$
$$L_s = \ln\left(\frac{\Gamma_I}{\Gamma_D}\right), \quad s \in \{1, \dots, 16\}$$

### B. Elsődleges Becslés
A 16 mérési alkalom átlaga:
$$\bar{L} = \frac{1}{16} \sum_{s=1}^{16} L_s, \quad \text{SE} = \frac{s_L}{\sqrt{16}}$$
A $99\%$-os kétoldali Student-$t$ konfidenciaintervallum ($df = 15$, $t_{0.005, 15} \approx 2.9467$):
$$\text{CI}_{99} = \left[\bar{L} - 2.9467 \cdot \text{SE}, \quad \bar{L} + 2.9467 \cdot \text{SE}\right]$$

### C. Döntési Szabály a 99%-os Konfidenciaintervallumból
1. **$0 \in \text{CI}_{99}$ és $+0.08 \notin \text{CI}_{99}$:** Az eredmény **összeegyeztethető a 0-val**, és **nem egyeztethető össze a +0.08-cal**.
2. **$+0.08 \in \text{CI}_{99}$ és $0 \notin \text{CI}_{99}$:** Az eredmény **összeegyeztethető a +0.08-cal**, és **nem egyeztethető össze a 0-val**.
3. **Egyik sincs benne:** Az eredmény **egyik pontjóslattal sem egyeztethető össze**.
4. **Mindkettő benne van:** Az eredmény **NEM DÖNTŐ**.

*Módszertani alapelv:* A benne maradó pont nem tekinthető bizonyított abszolút igazságnak. Elemzőváltás vagy korai megállás kizárva.

### D. Fail-Closed Adatkezelési Garanciák
- Kizárólag a hardveres technikai hiba (megszakadt job, kontrollelektronikai hiba) minősül érvénytelen mérésnek.
- $P_G(0)$ vagy $S(0)$ értéke alapján **tilos adatot kidobni**.
- Ha valamelyik ráta matematikailag nem definiálható ($S(T) \le 0$ vagy $S(0) \le 0$), a pre-regisztrált elsődleges terv kimenete **`NEM ERTEKELHETO (UNDEFINED RATES)`**. Csendes adatkihagyás szigorúan tiltott, minden mérési hibát tételesen dokumentálunk a riportban.

---

## 6. Modellellenőrzés és Diagnosztika ($D_2$)

Az egyexponenciális relaxációs modell ellenőrzése mind a 16 alkalomra és mindkét karra ($16 \times 2 = 32$ teszt):
$$D_2 = S(2T) - \frac{S(T)^2}{S(0)}$$

### Teljes Hibaterjedés (Delta-módszer)
Mivel $S(0)$, $S(T)$ és $S(2T)$ külön áramkörökből, független binomiális mintákból származnak:
$$\operatorname{Var}(S(t)) = \frac{P_E(t)(1 - P_E(t))}{N_E(t)} + \frac{P_G(t)(1 - P_G(t))}{N_G(t)}$$
$$\operatorname{Var}(D_2) = \operatorname{Var}(S(2T)) + \left(\frac{2 S(T)}{S(0)}\right)^2 \operatorname{Var}(S(T)) + \left(\frac{S(T)^2}{S(0)^2}\right)^2 \operatorname{Var}(S(0))$$
$$z = \frac{D_2}{\sqrt{\operatorname{Var}(D_2)}}, \quad p = 2 \cdot (1 - \Phi(|z|))$$

### Értelmezési Diagnosztika (NEM Blokk-kizárás!)
- Családi szignifikancia: 32 ellenőrzésre Bonferroni-korrekció összesített $\alpha = 0.01$ mellett:
  $$\alpha_{\text{bonf}} = \frac{0.01}{32} = 0.0003125 \implies z_{\text{crit}} \approx 3.605$$
- **Szerepe:** Diagnosztikai jelzés. Ha szignifikáns eltérés mutatkozik, az $L$ nem nevezhető igazolt egyexponenciális rátaeltérésnek, de a blokkokat **tilos kizárni**.

---

## 7. Keretbecslés és Költségtranszparencia

A mai 8 blokkos éles kalibráció alapján (`ibm_marrakesh`, Heron r2: 44 000 lövés / 24 másodperc tiszta QPU idő $\implies 0.545\text{ ms / lövés}$):

| Konfiguráció | Áramkör / alkalom | Lövés / alkalom | Összes lövés (16 alkalom) | Becsült tiszta QPU idő | Meglévő szabad keret | Hátralévő keret a mérés után |
|---|---|---|---|---|---|---|
| **Opció A: Mag (D + I)** | 12 | 10 000 | 160 000 | **~87.3 másodperc** | 432.0 másodperc | **~344.7 másodperc** |
| **Opció B: Mag + $D_{\text{fast}}$** | 16 | 13 000 | 208 000 | **~113.5 másodperc** | 432.0 másodperc | **~318.5 másodperc** |

> **Költség- és Keret-garancia:**  
> A teljes 16 alkalmas mérési kampány a meglévő 432 másodperces ingyenes IBM keretnek mindössze **20–26%-át** használja fel.  
> **Fizetős túlfutási kockázat: 0.0% (ZERO).**

---

## 8. Szimulációs Audit Eredményei (500 Kampány / Eset)

A `src/v3_simulator.py` futtatásának eredményei (naplózva a `results/v3_simulator_test_log.txt` fájlba):

1. **Case 1: $L = 0.00$ (Markov referencia, $\sigma = 0.03$):**
   - Átlagos pontbecslés: $-0.0008 \pm 0.0148$, $99\%$-os CI félszélesség: $\pm 0.0425$.
   - Döntés: **97.8%** (489/500) helyesen *"Összeegyeztethető 0-val, nem +0.08-cal"*.
   - Álpozitív arány a +0.08-ra: **0.00%** (0/500).
2. **Case 2: $L = +0.08$ (Máté jóslat, $\sigma = 0.03$):**
   - Átlagos pontbecslés: $+0.0804 \pm 0.0148$.
   - Döntés: **98.4%** (492/500) helyesen *"Összeegyeztethető +0.08-cal, nem 0-val"*.
3. **Case 3: Köztes érték ($L = +0.04$):**
   - A döntések megoszlanak a két határeset és a *"Nem döntő"* (21.6%) / *"Egyikkel sem"* (9.6%) kategóriák között.
4. **Case 4: Szivárgási modell ($|2\rangle \to |1\rangle \to |0\rangle$ kaszkád):**
   - Kimutatja az enyhe szivárgási műterméket ($+0.0041$), és a $D_2$ Bonferroni teszt megfelelően reagál a nemlinearitásra.
5. **Case 5: Időbeli függés (AR(1) drift a 16 alkalom között, $\rho = 0.50$):**
   - A $99\%$-os CI valós lefedése erős autokorreláció mellett is **96.4%** marad (92.0% helyes döntési arány).
6. **Case 6: Matematikai határesetek és hibás logaritmustartomány:**
   - Negatív kontraszt vagy nem pozitív ráta esetén az elemző azonnal **`NEM ERTEKELHETO (UNDEFINED RATES)`** jelzéssel áll le, kizárva a csendes adatelhagyást.
