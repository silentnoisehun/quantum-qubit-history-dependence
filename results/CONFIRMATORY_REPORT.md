# Qubit-Előzményfüggés Konfirmatív Mérési Jelentés (Revízió v1.2)
**Dátum (UTC):** 2026-11-22T08:48:22.389826+00:00  
**Backend:** `ibm_marrakesh` (Heron r2, 156-qubit QPU)  
**Qubitpár:** Elsődleges $q=21$, Szomszéd $q'=20$  
**Hivatalos Döntési Kategória:** **`NEM DONTO`**  

---

## 1. Vezetői Összefoglaló és Végső Ítélet

A pre-regisztrált protokoll szerint 8 független mérési blokk (összesen 352 áramkör, 352 000 lövés, 192 másodperc tiszta QPU idő) futott le az `ibm_marrakesh` Heron r2 processzorán.

### Fő Eredmény: Relaxációs Lecsengési Ráta ($L(\tau_0)$)

A döntési szabályzat értelmezési bizonytalansága (azaz hogy a 2T modellpróbát csak a $D$-karra vagy mindkét karra kell alkalmazni) miatt mindkét blokkhalmaz eredményét egyenrangúan közöljük:

- **6 Szigorúan Érvényes Blokk (D és I 2T modellpróbával):** $\bar{L} = +0.0360 \pm 0.0215$ ($t(5) = 1.672, p = 0.1553$, $99\%\text{ CI} = [-0.0508, +0.1228]$).
- **Mind a 8 Blokk Összesítve:** $\bar{L} = +0.0220 \pm 0.0193$ ($t(7) = 1.141, p = 0.2915$, $99\%\text{ CI} = [-0.0454, +0.0894]$).
- **Döntés:** Mindkét blokkhalmazra egyértelműen **`NEM DONTO`**. A p-értékek ($p = 0.16$ és $p = 0.29$) nem érik el az $\alpha = 0.01$-es szignifikanciaszintet. A 99%-os konfidenciaintervallumok a null-hipotézist ($0.00$) és a $+10\%$-os jóslatot is lefedik, így a jelenlegi adatok mellett egyik sem zárható ki és egyik sem bizonyított.

*Megjegyzés a blokkhalmazokhoz:* Az $L(\tau_0)$ főbecslése a 6 érvényes blokkból (és a 8 blokkos összevetésből) származik, míg a másodlagos tesztek (S1–S6) és a $\tau$-lecsengési görbe mind a 8 mért blokk adatait felhasználják a maximális statisztikai erő érdekében.

---

## 2. Megfigyelt Másodlagos Kontraszt: G-Előkészítés Utáni Kiolvasási Különbség (S5)

Miközben a relaxációs ráta eltérése nem döntő, a pre-regisztrált **S5 másodlagos teszt** határozott kiolvasási kontrasztot mutatott ki a $G$-előkészítés után a két kar között:

- **Megfigyelt kontraszt ($P_G^D(0) - P_G^I(0)$):** átlagosan **+0.425 százalékpont** ($0.00425$), $8$ blokk páros próba: $t(7) = 5.340, p = 0.000508$.
- **Holm-Bonferroni korrekció:** A pre-regisztrált 5 tesztelhető konfirmatív másodlagos hipotéziscsaládban ($m=5$) a legszigorúbb korrigált küszöb $\alpha_{{\text{{adj}}}} = 0.01 / 5 = 0.0020$. Mivel $p = 0.00051 < 0.0020$, a kiolvasási kontraszt **statisztikailag szignifikáns**.

> **Módszertani és Fizikai Határ:**  
> A mérés megbízhatóan kimutatja a $D$ és $I$ karok közötti kiolvasási kontrasztot a $G$-előkészítés után. Ebből önmagában **nem következik** romló reset vagy ötszörös valódi gerjesztett maradékpopuláció: a fizikai gerjesztettség, a magasabb állapotú szivárgás ($|2\rangle$) és a kiolvasási torzítás ebben az egycsatornás mérésben nincs szétválasztva. A kísérlet a megfigyelt kontrasztot rögzíti, a mögöttes mikroszkopikus okot nyitva hagyja.

---

## 3. Blokkonkénti Eredmények és Kapu-Audit

| Blokk | Job ID | $S(0)_D$ | $S(0)_I$ | $P_G(0)_D$ | $P_G(0)_I$ | $L(\tau_0)$ | MC Diff $D$ | MC Diff $I$ | Kapu Állapot |
|---|---|---|---|---|---|---|---|---|---|
| 0 | `dbvkej0l0c4s739lsvug` | 0.9790 | 0.9910 | 0.0080 | 0.0030 | +0.0497 | 0.0077 | 0.0297 | **ÉRVÉNYES** |
| 1 | `dc1a72inj2vs73df3ebg` | 0.9910 | 0.9880 | 0.0010 | 0.0000 | +0.0837 | 0.0299 | 0.0476 | **ÉRVÉNYES** |
| 2 | `dc1a73dhdvas73bkj2q0` | 0.9900 | 0.9900 | 0.0050 | 0.0010 | +0.0364 | 0.0443 | 0.0426 | **ÉRVÉNYES** |
| 3 | `dc1a745s2omc738ac0k0` | 0.9830 | 0.9930 | 0.0060 | 0.0000 | -0.0576 | 0.0232 | 0.0142 | **ÉRVÉNYES** |
| 4 | `dc1a74thdvas73bkj2rg` | 0.9840 | 0.9920 | 0.0050 | 0.0010 | +0.0848 | 0.0106 | 0.0407 | **ÉRVÉNYES** |
| 5 | `dc1a75thdvas73bkj2t0` | 0.9840 | 0.9900 | 0.0090 | 0.0020 | +0.0190 | 0.0274 | 0.0364 | **ÉRVÉNYES** |
| 6 | `dc1a76lhdvas73bkj2u0` | 0.9910 | 0.9960 | 0.0030 | 0.0010 | -0.0530 | 0.0497 | 0.0602 | **HULLOTT (MC)** |
| 7 | `dc1a77anj2vs73df3eh0` | 0.9860 | 0.9910 | 0.0050 | 0.0000 | +0.0128 | 0.0628 | 0.0133 | **HULLOTT (MC)** |

*Megjegyzés a modellpróbához:* A kritikus küszöb $2.576 \times \sqrt{0.5 / 1000} = 0.0576$.
- A **6. blokk** az $I$-kar $2T$ modellpróbáján hullott el ($0.0602 > 0.0576$).
- A **7. blokk** a $D$-kar $2T$ modellpróbáján hullott el ($0.0628 > 0.0576$).
- A maradék **6 blokk** (0–5) mindkét karon szigorúan átment, teljesítve a pre-regisztráció minimum követelményét ($\ge 6$).

---

## 4. Kondicionáló Karok Elemzése

- **Periodikus hajtás ($D$ vs $I$):** $\bar{L} = +0.0220 \pm 0.0193$ ($t(7) = 1.141, p = 0.2915$)
- **Szomszéd hajtás ($Nb$ vs $I$):** $\bar{L} = +0.0091 \pm 0.0142$ ($p = 0.5391$)
- **Hajtási ráta különbség ($D$ vs $D_{\text{fast}}$):** $\bar{L}_D - \bar{L}_{D_{\text{fast}}} = \ln(\Gamma_{D_{\text{fast}}} / \Gamma_D) = \mathbf{+0.0046} \pm 0.0257$ ($p = 0.8640$)
- **Gyorsított hajtás az üresjárathoz ($D_{\text{fast}}$ vs $I$, feltáró):** $\bar{L} = +0.0174 \pm 0.0137$ ($p = 0.2456$)
- **Üresjárat ($I$):** $0.0000$ (referencia)

**Módszertani Megjegyzés:** Az egymást kölcsönösen átfedő konfidenciaintervallumok miatt a karok átlagai közötti különbségek nem tekinthetők igazolt fizikai hierarchiának.

### Pre-regisztrált Másodlagos Hipotéziscsalád (Holm-Bonferroni Korrekció, m=5)

| Hipotézis | Teszt Megnevezése | Mért Statisztika / Kontraszt | Nyers p-érték | Holm-küszöb (m=5) | Eredmény |
|---|---|---|---|---|---|
| **S5** | G-előkészítés utáni kiolvasási kontraszt | $\Delta P_G(0) = +0.425\%$ | **0.000508** | $\alpha_1 = 0.0020$ | **SZIGNIFIKÁNS** |
| **S2** | Szomszéd qubit áthallás ($Nb$ vs $I$) | $\bar{L} = +0.0091$ | 0.5391 | $\alpha_2 = 0.0025$ | Nem szignifikáns |
| **S6** | Kaszkád szivárgási jelkontraszt | $\Delta = +0.0015$ | 0.5630 | $\alpha_3 = 0.0033$ | Nem szignifikáns |
| **S1** | $\tau$-lecsengési trend ($L(\tau)$ vs $\ln\tau$) | Meredekség: -0.0004 | 0.7825 | $\alpha_4 = 0.0050$ | Nem szignifikáns |
| **S3** | Hajtási rátafüggés ($D$ vs $D_{\text{fast}}$) | $\bar{L}_D - \bar{L}_{D_{\text{fast}}} = +0.0046$ | 0.8640 | $\alpha_5 = 0.0100$ | Nem szignifikáns |

- **S4 (Carry-over hatás):** A pre-regisztráció szerint tiszta vs. váltakozó blokksorrendet hasonlított volna össze, de az éles QPU futtatásban a hardveres drift kiküszöbölésére minden áramkör blokkon belül összefésült (interleaved) szekvenciában futott le, így az S4 közvetlenül nem volt megfigyelhető.
- **Feltáró teszt ($D_{\text{fast}}$ vs $I$):** $\bar{L} = +0.0174 \pm 0.0137$ ($p = 0.2456$), a pre-regisztrált 5-ös konfirmatív családon kívül értékelt feltáró vizsgálat.


---

## 5. Elméleti Jóslatok Szintézise: Máté (H1) vs Instinct (H0)

| Mérőszám / Elem | Máté Irányhipotézise (H1) | Instinct Elméleti Referenciája (H0) | QPU Empirikus Mérés (Heron r2) |
|---|---|---|---|
| **$L(\tau_0)$ jóslat** | **$+0.10$** ($\approx +10.5\%$ lassulás) | **$0.00$** (markovi állandóság) | **+0.0360** (6 blokk) / **+0.0220** (8 blokk) |
| **99%-os Konfidenciasáv** | $[+0.05, +0.15]$ várt | $[-\delta_{\text{eq}}, +\delta_{\text{eq}}] = [-0.075, 0.075]$ | **$[-0.0508, +0.1228]$** (Mindkét jóslatot fedi) |
| **Effektív $T_{1,D}$ (reciprok ráta)** | $\approx 242\ \mu\text{s}$ ($+0.10$-nél) | $219.39\ \mu\text{s}$ (azonos az $I$-vel) | $181.3\ \mu\text{s}$ ($T_{1,I} = 175.1\ \mu\text{s}$) |
| **$G$-kiolvasási kontraszt ($\Delta P_G(0)$)** | $\le 0.005$ | $0.0000$ | **+0.00425** (**$p = 0.00051$, SZIGNIFIKÁNS**) |

*Megjegyzés a T1 értékekhez:* A közölt $T_{1,D} \approx 181.3\ \mu\text{s}$ és $T_{1,I} \approx 175.1\ \mu\text{s}$ értékek a 6 megtartott blokk átlagos rátáinak reciprokai ($1 / \bar{\Gamma}$), nem a blokkonkénti $T_1$-ek számtani átlagai (a $D$ blokkonkénti tartománya $\approx 146\dots 324\ \mu\text{s}$).

### Instinct Analitikus Levezetése és Episztemikus Határa (ld. `docs/H0_REFERENCE_DERIVATION.md`):
1. **Analitikus alap:** A pilot $T_1 = 219.39\ \mu\text{s}$ és $S(0) = 0.9891$ mellett $S(T)/S(0) = \exp(-220/219.39) = 0.366862 \implies S(T) \approx 0.362864$. Ha a környezet változatlan, $\Gamma_I = \Gamma_D \implies L(\tau_0) = 0.00$.
2. **Az episztemikus korlát:** A környezet változatlansága feltevés. A pilot mérés nem határozza meg a 64 kapu mikroszkopikus csatolását ($\Delta \Gamma, \tau_{\text{mem}}$); ezek nélkül a valódi hardver hatásmérete elméletileg nem volt egyértelműen kiszámítható.
3. **Máté jóslatának átszámítása:** Ha $T_{1,I} = 219.39\ \mu\text{s}$, a $+0.08$-as hatás $T_{1,D} = 237.67\ \mu\text{s}$-ot ($7.69\%$-os rátacsökkenést) jelentene.

---

## 6. Szimulációs Audit és Szivárgási Sérülékenység (`src/simulator.py`)

A pre-regisztrációs szimulátor futtatási eredményei (reprodukálva a `python src/simulator.py` paranccsal, naplózva a `results/simulation_validation_output.txt` fájlba):
- **Null-kalibráció (H0):** 1000 szimulált kampány $5\%$ inter-block drift mellett $\implies$ Álpozitív arány: **$0.70\%$** (Cél: $\le 1.0\%$).
- **Detektálási erő (MDE):** $7.5\%$-os injektált lassulás mellett az elemző **$500$-ból $456$ alkalommal ($91.20\%$)** sikeresen kimutatta az effektust.
- **Szimmetrikus szivárgás:** $S(t)$ levonás miatt csupán **$0.20\%$** álpozitív.
- **Aszimmetrikus szivárgási próba ($|2\rangle \to |1\rangle \to |0\rangle$ kaszkád játékmodell):** $30\%$ aszimmetria mellett **$500$-ból $23$ alkalommal ($4.60\%$)** hamis lassulás ($L > 0$) keletkezett.

> **Módszertani Megjegyzés:**  
> A 4.6% egy játékmodellben feltárt elemzési sérülékenység (nem hardveres szivárgás bizonyítéka), amely arra figyelmeztet, hogy az aszimmetrikus szivárgás képes enyhe látszólagos lassulást generálni az 1%-os szinten. A valós QPU mérésben a relaxációs ráta eltérése nem döntő ($p = 0.16$), miközben a $G$-előkészítés utáni kiolvasási kontraszt ($\Delta P_G(0) = +0.425\%$, $p = 0.00051$) szignifikánsan jelen van.