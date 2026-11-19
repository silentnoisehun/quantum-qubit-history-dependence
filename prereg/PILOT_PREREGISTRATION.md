# Pilot Előregisztráció — Qubit Előzményfüggés ("Qubit Gumija")
**Verzió:** 0.1 (Pilot)  
**Időbélyeg:** 2026-11-19T18:09:00Z  
**Backend:** `ibm_marrakesh`  
**Elsődleges Qubit ($q$):** 21  
**Szomszéd Qubit ($q'$):** 20  

---

## 1. A Pilot Célja és Korlátai (NINCS ÁLLÍTÁS)

A pilot mérés kizárólag a technikai megvalósíthatóság és a hardver-paraméterek kalibrálására szolgál.
**A pilot adatai alapján semmilyen fizikai állítás vagy konklúzió nem vonható le.**
A megerősítő elemzésből a pilot adatai szigorúan kizárásra kerülnek.

### Mit mér a pilot:
1. $T_1$ relaxációs idő empirikus ellenőrzése $q=21$-en 8 pontos lecsengési görbével ($0 \dots 3 T_1$).
2. Valódi hardveres futásidő és QPU-költség pontos mérése az IBM Runtime rendszerében.
3. A fordítási audit (optimization_level=0, barrier-védelem, gate integrity) hardveres visszaigazolása.
4. A blokkon belüli szórás ($\sigma_L$) becslése a végleges megerősítő mintaméret (blokkszám, lövésszám) rögzítéséhez.
5. Az érvényességi kapuk (minimális kontraszt $S(0)$, maximális alapzaj $P_G(0)$) empirikus küszöbeinek beállítása.

### Mit NEM tesz a pilot:
- **Az $L(\tau_0)$ előjele a pilot során rejtve marad (blinded):** az elemző kizárólag a karokon átlagolt statisztikákat és a belső szórást jeleníti meg, a különbségi hipotézist nem értékeli.

---

## 2. Hardveres és Időzítési Konfiguráció

- **Backend:** `ibm_marrakesh` (Heron r1 processzor)
- **Mintavételi ütem ($dt$):** $4.0\text{ ns}$
- **Granularitás:** 1 minta
- **Minimális delay:** 2 minta ($8.0\text{ ns}$)
- **$X$ kapu időtartama:** $36.0\text{ ns}$ ($9\text{ dt}$)
- **Reset időtartama:** $2720.0\text{ ns}$ ($680\text{ dt}$)
- **Mérés időtartama:** $2684.0\text{ ns}$ ($671\text{ dt}$)
- **Repetition delay (`rep_delay`):** $250.0\ \mu\text{s}$ (rögzített alapértelmezett)
- **Kondicionáló ablak ($T_c$):** $16.128\ \mu\text{s}$ ($4032\text{ dt}$)
- **Pulzusszám ($N$):** 64
- **Pre-reset teljes időtartam:** $\tau_{\max} + T_c = 64.0\ \mu\text{s} + 16.128\ \mu\text{s} = 80.128\ \mu\text{s}$ (minden áramkörben azonos!)

---

## 3. Pilot Job Összetétele

1. **44 kampány áramkör:**
   - $D$ és $I$ karok: 4 $\tau$ ($8\text{ ns}, 4\ \mu\text{s}, 16\ \mu\text{s}, 64\ \mu\text{s}$) $\times$ 4 állapot ($G_0, G_T, E_0, E_T$) = 32 áramkör
   - Modell-ellenőrzés: $D$ és $I$ $\tau_0$-nál $t=2T$ késleltetéssel $\times$ 2 állapot ($G, E$) = 4 áramkör
   - Kontroll karok: $Nb$ és $D_{\text{fast}}$ $\tau_0$-nál $\times$ 4 állapot = 8 áramkör
2. **8 T1 kalibrációs áramkör:**
   - $t \in [0, 72, 144, 216, 288, 360, 432, 504]\ \mu\text{s}$
3. **Összesen:** 52 áramkör, 1000 lövés áramkörönként egyetlen összevont pilot jobban.

---

## 4. Lefagyasztott Kód és Manifest Hash-ek

| Komponens | Fájl | SHA256 Hash |
|---|---|---|
| Manifest | `prereg/manifest_audit.json` | `4a1b8b832623474c72b5d43f57e0633993169919c89908b99c48499ea292af19` |
| Áramkörépítő | `src/circuit_builder.py` | `ff672b0d0ad0be9001d1f1608940565b7372a9fee9fb773e72dde8dce61bd8c6` |
| Fordítási audit | `src/audit_transpiler.py` | `efb0d00c1f43e214db0dd73c87395b0d3cd0540573cd3dd4c36f91163a71c11b` |
| Elemző pipeline | `src/analysis.py` | `9213456b4379386fcb2c679d5d15a0ac9a50dfee50eace7feefe4e430f613a3f` |
| Szimulátor | `src/simulator.py` | `245ab550569389b1eef38035b19d519f270f47e46daa0402a2e4412f0a5a1033` |
