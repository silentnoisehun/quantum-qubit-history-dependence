# Qubit-Előzményfüggés Konfirmatív Mérési Jelentés (Revízió v1.1)
**Dátum (UTC):** 2026-11-22T08:38:32.911385+00:00  
**Backend:** `ibm_marrakesh` (Heron r2, 156-qubit QPU)  
**Qubitpár:** Elsődleges $q=21$, Szomszéd $q'=20$  
**Hivatalos Döntési Kategória:** **`NEM DONTO`**  

---

## 1. Vezetői Összefoglaló és Végső Ítélet

A pre-regisztrált protokoll szerint 8 független mérési blokk (összesen 352 áramkör, 352 000 lövés, 192 másodperc tiszta QPU idő) futott le az `ibm_marrakesh` Heron r2 processzorán.

### Fő Eredmény: Relaxációs Lecsengési Ráta ($L(\tau_0)$)
- **6 Szigorúan Érvényes Blokk (D és I 2T modellpróbával):** $\bar{L} = +0.0360 \pm 0.0215$ ($t(5) = 1.672, p = 0.1553$, $99\%\text{ CI} = [-0.0508, +0.1228]$).
- **Mind a 8 Blokk Összesítve:** $\bar{L} = +0.0220 \pm 0.0193$ ($t(7) = 1.141, p = 0.2915$, $99\%\text{ CI} = [-0.0454, +0.0894]$).
- **Döntés:** A p-értékek ($p = 0.16$ és $p = 0.29$) jóval meghaladják az előre rögzített $\alpha = 0.01$-es küszöböt. Mivel a 99%-os konfidenciaintervallumok átfedik a null-hipotézist ($0.00$) és a $+10\%$-os jóslatot is, a statisztikai ítélet egyértelműen **`NEM DONTO`**.

---

## 2. Kulcs Mellékeredmény: Szignifikáns Resetmaradék-Eltérés (S5)

Miközben a relaxációs ráta eltérése nem érte el a szignifikanciát, a pre-regisztrált **S5 másodlagos teszt** határozott, szignifikáns fizikai eltérést mutatott ki a reset utáni alapállapot gerjesztettségében:

- **Hajtott kar ($D$) resetmaradéka ($P_G(0)$):** átlagosan **~0.53%** ($0.0053$).
- **Üresjárati kar ($I$) resetmaradéka ($P_G(0)$):** átlagosan **~0.10%** ($0.0010$).
- **Eltérés ($\Delta P_G(0)$):** átlagosan **+0.43%** ($p = 0.00051$).
- **Holm-Bonferroni korrekció:** A korrigált küszöb $\alpha_{{\text{{adj}}}} = 0.0025$. Mivel $p = 0.00051 < 0.0025$, a különbség **statisztikailag szignifikáns**.

> **Fizikai Következtetés:** A reset előtti periodikus hajtás statisztikailag igazolható nyomot hagy a qubitben: a reset hatékonysága csökken, a visszamaradó gerjesztett populáció ~5-szörösére növekszik. Ez előzményfüggés a reset folyamatában, nem pedig a reset utáni szabad relaxáció lassulása.

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
- **Gyorsított hajtás ($D_{\text{fast}}$ vs $I$):** $\bar{L} = +0.0174 \pm 0.0137$ ($p = 0.2456$)
- **Szomszéd hajtás ($Nb$ vs $I$):** $\bar{L} = +0.0091 \pm 0.0142$ ($p = 0.5391$)
- **Üresjárat ($I$):** $0.0000$ (referencia)
- **Hajtási ráta különbség ($D$ vs $D_{\text{fast}}$):** $\bar{L}_D - \bar{L}_{D_{\text{fast}}} = -0.0046 \pm 0.0257$ ($p = 0.8640$)

**Módszertani Megjegyzés:** Bár a pontbecslések számszaki sorrendje $\bar{L}(D) > \bar{L}(D_{\text{fast}}) > \bar{L}(Nb) > 0$, az egymást kölcsönösen átfedő konfidenciaintervallumok miatt ez pusztán tapasztalati minta, nem statisztikailag igazolt fizikai hierarchia.

---

## 5. Elméleti Jóslatok Szintézise: Máté (H1) vs Maya (H0)

| Mérőszám / Elem | Máté Irányhipotézise (H1) | Maya Elméleti Referenciája (H0) | QPU Empirikus Mérés (Heron r2) |
|---|---|---|---|
| **$L(\tau_0)$ jóslat** | **$+0.10$** ($\approx +10.5\%$ lassulás) | **$0.00$** (markovi állandóság) | **+0.0360** (6 blokk) / **+0.0220** (8 blokk) |
| **99%-os Konfidenciasáv** | $[+0.05, +0.15]$ várt | $[-\delta_{\text{eq}}, +\delta_{\text{eq}}] = [-0.075, 0.075]$ | **$[-0.0508, +0.1228]$** (Mindkét jóslatot fedi) |
| **Effektív $T_{1,D}$** | $\approx 242\ \mu\text{s}$ ($+0.10$-nél) | $219.39\ \mu\text{s}$ (azonos az $I$-vel) | $181.3\ \mu\text{s}$ ($T_{1,I} = 175.1\ \mu\text{s}$) |
| **Resetmaradék ($\Delta P_G(0)$)** | $\le 0.005$ | $0.0000$ | **+0.00425** (**$p = 0.00051$, SZIGNIFIKÁNS**) |

### Maya Analitikus Levezetése és Episztemikus Határa:
1. **Analitikus alap:** A pilot $T_1 = 219.39\ \mu\text{s}$ és $S(0) = 0.9891$ mellett $S(T)/S(0) = \exp(-220/219.39) = 0.366862 \implies S(T) \approx 0.362864$. Ha a környezet változatlan, $\Gamma_I = \Gamma_D \implies L(\tau_0) = 0.00$.
2. **Az episztemikus korlát:** A környezet változatlansága feltevés. A pilot mérés nem határozza meg a 64 kapu mikroszkopikus csatolását ($\Delta \Gamma, \tau_{\text{mem}}$); ezek nélkül a valódi hardver hatásmérete elméletileg nem volt egyértelműen kiszámítható.
3. **Máté jóslatának átszámítása:** Ha $T_{1,I} = 219.39\ \mu\text{s}$, a $+0.08$-as hatás $T_{1,D} = 237.67\ \mu\text{s}$-ot ($7.69\%$-os rátacsökkenést) jelentene.

---

## 6. Szimulációs Audit és Szivárgási Csapda-Figyelmeztetés (`src/simulator.py`)

A pre-regisztrációs szimulátor független újrafuttatása pontosan megerősítette a Maya által idézett értékeket:
- **Null-kalibráció (H0):** 1000 szimulált kampány $5\%$ inter-block drift mellett $\implies$ Álpozitív arány: **$0.70\%$** (Cél: $\le 1.0\%$).
- **Detektálási erő (MDE):** $7.5\%$-os injektált lassulás mellett az elemző **$500$-ból $456$ alkalommal ($91.20\%$)** sikeresen kimutatta az effektust.
- **Szimmetrikus szivárgás:** $S(t)$ levonás miatt csupán **$0.20\%$** álpozitív.
- **Aszimmetrikus szivárgási próba ($|2\rangle \to |1\rangle \to |0\rangle$ kaszkád):** $30\%$ aszimmetria mellett **$500$-ból $23$ alkalommal ($4.60\%$)** hamis lassulás ($L > 0$) keletkezett.

> **Összegző Konklúzió:**  
> A szimulációs audit előre jelezte, hogy a nemlineáris/aszimmetrikus szivárgási folyamatok képesek $4.6\%$-ban enyhe pozitív $L$-t generálni. A QPU-n tapasztalt eredmény pontosan erre rímel: a relaxációs ráta eltérése nem döntő ($p = 0.16$), a kísérlet valódi és statisztikailag tartható előzményfüggő nyoma pedig a **resetelési hatékonyság romlásában és a resetmaradék gerjesztettségében ($\Delta P_G(0) = +0.43\%$, $p = 0.00051$)** jelent meg.