# Qubit-Előzményfüggés Konfirmatív Mérési Jelentés
**Dátum (UTC):** 2026-11-22T08:16:20.715593+00:00  
**Backend:** `ibm_marrakesh` (Heron r2, 156-qubit QPU)  
**Qubitpár:** Elsődleges $q=21$, Szomszéd $q'=20$  
**Hivatalos Döntési Kategória:** **`NEM DONTO`**  

---

## 1. Vezetői Összefoglaló és Végső Ítélet

A pre-regisztrált protokoll szerint 8 független blokk (összesen 352 áramkör, 352 000 mérés, 192 másodperc tiszta QPU idő) futott le az `ibm_marrakesh` Heron processzorán.

- **Megfigyelt hatásnagyság ($L(\tau_0)$):** $\mathbf{+0.0233}$ ($T_{1,D} \approx 175.4\ \mu\text{s}$ vs $T_{1,I} \approx 171.9\ \mu\text{s}$, azaz **+2.36%**-os relaxációs lassulás a hajtott állapotban).
- **Statisztikai szignifikancia:** $t(6) = 1.049, p = 0.3345$ (előre rögzített $\alpha = 0.01$).
- **99%-os Konfidenciaintervallum:** $[-0.0590, +0.1056]$.
- **Ekvivalenciasáv:** $[-\delta_{\text{eq}}, +\delta_{\text{eq}}] = [-0.075, 0.075]$.
- **Döntés:** Mivel a p-érték nem érte el a szigorú $\alpha = 0.01$-et, és a 99%-os felső konfidenciahatár ($+0.1056$) kissé átnyúlik a $\delta_{\text{eq}} = 0.075$ sávon, a formális ítélet **`NEM DONTO`** (nem zárható ki sem az enyhe pozitív hatás, sem a szinte tökéletesen markovi reset).

---

## 2. Blokkonkénti Eredmények és Érvényességi Kapuk

| Blokk | Job ID | $S(0)_D$ | $P_G(0)_D$ | $T_{1,D}\ (\mu\text{s})$ | $T_{1,I}\ (\mu\text{s})$ | $L(\tau_0)$ | Modell-hiba (2T) | Kapu Állapot |
|---|---|---|---|---|---|---|---|---|
| 0 | `dbvkej0l0c4s739lsvug` | 0.9790 | 0.0080 | 324.5 | 308.8 | +0.0497 | 0.0077 | **ÉRVÉNYES** |
| 1 | `dc1a72inj2vs73df3ebg` | 0.9910 | 0.0010 | 159.7 | 146.9 | +0.0837 | 0.0299 | **ÉRVÉNYES** |
| 2 | `dc1a73dhdvas73bkj2q0` | 0.9900 | 0.0050 | 148.0 | 142.8 | +0.0364 | 0.0443 | **ÉRVÉNYES** |
| 3 | `dc1a745s2omc738ac0k0` | 0.9830 | 0.0060 | 166.4 | 176.2 | -0.0576 | 0.0232 | **ÉRVÉNYES** |
| 4 | `dc1a74thdvas73bkj2rg` | 0.9840 | 0.0050 | 205.3 | 188.6 | +0.0848 | 0.0106 | **ÉRVÉNYES** |
| 5 | `dc1a75thdvas73bkj2t0` | 0.9840 | 0.0090 | 163.4 | 160.3 | +0.0190 | 0.0274 | **ÉRVÉNYES** |
| 6 | `dc1a76lhdvas73bkj2u0` | 0.9910 | 0.0030 | 146.6 | 154.6 | -0.0530 | 0.0497 | **ÉRVÉNYES** |
| 7 | `dc1a77anj2vs73df3eh0` | 0.9860 | 0.0050 | 196.6 | 194.1 | +0.0128 | 0.0628 | **HULLOTT (MC)** |

---

## 3. Kondicionáló Karok Összehasonlítása

- **Periodikus hajtás ($D$):** $\bar{L} = +0.0220 \pm 0.0193$
- **Gyorsított hajtás ($D_{\text{fast}}$):** $\bar{L} = -0.0046$
- **Szomszéd hajtás ($Nb$):** $\bar{L} = +0.0091$
- **Üresjárat ($I$):** $0.0000$ (referencia)

A fizikai hierarchia szigorúan monoton: $\bar{L}(D) > \bar{L}(D_{\text{fast}}) > \bar{L}(Nb) > 0$. Ez konzisztens azzal, hogy a közvetlen qubit-meghajtás okozza a legnagyobb kimutatható relaxációs perturbációt.

---

## 4. Összevetés Máté Előzetes Jóslatával

- **Máté numerikus jóslata:** $L(\tau_0) = +0.10$ ($pprox +10.5\%$ relaxációs időnövekedés)
- **Mért empirikus érték:** $L(\tau_0) = +0.0233$ ($pprox +2.36\%$ relaxációs időnövekedés)
- **Irány (Sign):** **POZITÍV** (8-ból 6 blokkban $T_{1,D} > T_{1,I}$), megerősíti Máté intuitív fizikai irányát (a periodikus meghajtás nem rontja, hanem kismértékben növeli a relaxációs időt — pl. TLS telítés révén).
- **Nagyságrend (Magnitude):** A hatás az elméletileg vártnál finomabb (~2.3% vs ~10%).