# Qubit-Előzményfüggés Konfirmatív Mérési Jelentés (Revízió v1.1)
**Dátum (UTC):** 2026-11-22T08:23:20.232505+00:00  
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

## 4. Kondicionáló Karok és Jóslatok Helyzete

- **Periodikus hajtás ($D$):** $\bar{L} = +0.0220 \pm 0.0193$
- **Gyorsított hajtás ($D_{\text{fast}}$):** $\bar{L} = -0.0046$
- **Szomszéd hajtás ($Nb$):** $\bar{L} = +0.0091$
- **Üresjárat ($I$):** $0.0000$ (referencia)

**Módszertani Megjegyzés:** Bár a pontbecslések számszaki sorrendje $\bar{L}(D) > \bar{L}(D_{\text{fast}}) > \bar{L}(Nb) > 0$, az egymást átfedő hibahatárok miatt ez pusztán tapasztalati tendencia, nem igazolt fizikai hierarchia.

**Jóslat-összevetés:**
- Máté jóslata ($L = +0.10$) és a null-hipotézis ($L = 0.00$) egyaránt a 99%-os konfidenciaintervallumon ($[-0.0508, +0.1228]$) belül helyezkedik el.
- A jelenlegi adatmennyiség mellett a 10%-os hatás sem zárható ki, de nem is igazolt.
- A kísérlet valódi, statisztikailag tartható előzményfüggő hatása a **resetmaradékban ($\Delta P_G(0)$)** mutatkozott meg.