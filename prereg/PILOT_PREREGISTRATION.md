# Pilot Előregisztráció — Qubit Előzményfüggés ("Qubit Gumija")
**Verzió:** 0.3 (Pilot Frozen Spec)  
**Időbélyeg:** 2026-11-19T17:45:00Z (UTC)  
*(Megjegyzés: A 17:08:50 UTC-s kezdeti v0.1 fagyasztást felülírta [SUPERSEDED] a 17:30 / 17:45 UTC fagyasztás a kondicionáló ágak szomszéd-párhuzamosításának és scheduled timing auditjának bevezetése miatt.)*  
**Backend:** `ibm_marrakesh` (Heron r2 processzor, 156 fizikai qubit)  
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
3. A fordítási audit (`optimization_level=0`, slot-szintű barrier-védelem, gate integrity) hardveres visszaigazolása.
4. A blokkon belüli szórás ($\sigma$) becslése a végleges megerősítő mintaméret (blokkszám, lövésszám) rögzítéséhez.
5. Az érvényességi kapuk (minimális kontraszt $S(0)$, maximális alapzaj $P_G(0)$) empirikus küszöbeinek beállítása.

### Szigorú Vakítási Szabály (Blinded Gate):
- **Az $L(\tau_0)$ előjele és nagysága a pilot során szigorúan rejtve marad (blinded):**  
  A fagyasztott `pilot_blind_analysis.py` kizárólag a karokon átlagolt mennyiségeket (kontraszt $S(0)$, alapreferencia $P_G(0)$, egyedi pontok szórása és $T_1$ illesztés) adja ki a küszöbök beállításához. Nem számol irányt, különbséget, és nem hoz döntési ítéletet.

---

## 2. Qubit Kiválasztási Szabály (Determinisztikus)

A mérési qubitpár ($q, q'$) kiválasztása a backend napi kalibrációs adataiból automatizáltan történt (`fetch_backend_data.py`):
1. **Kiolvasási hiba:** az elsődleges qubit kiolvasási hibája a chip legjobb negyedében van ($RO_{\text{err}} \le Q_{25} = 0.007$).
2. **$T_1$ medián-közeliség:** a qubit $T_1$ értéke minimális távolságra van a backend medián $T_1$-étől (medián: $166.4\ \mu\text{s}$, $q=21$ értéke: $168.29\ \mu\text{s}$).
3. **Szomszéd qubit feltétel:** rendelkezik közvetlen fizikai csatolással bíró szomszéddal ($q'$), amelynek kiolvasási hibája a chip jobbik felében van ($RO_{\text{err}} \le Q_{50}$). Kiválasztva: $q'=20$ ($RO_{\text{err}} = 0.0059$, $T_1 = 129.7\ \mu\text{s}$).

---

## 3. Hardveres és Időzítési Konfiguráció

- **Backend:** `ibm_marrakesh` (Heron r2 processzor, 156 qubit)
- **Mintavételi ütem ($dt$):** $4.0\text{ ns}$
- **Granularitás:** 1 minta ($4\text{ ns}$)
- **Minimális delay:** 2 minta ($8.0\text{ ns}$)
- **$X$ kapu időtartama:** $36.0\text{ ns}$ ($9\text{ dt}$)
- **Reset időtartama:** $2720.0\text{ ns}$ ($680\text{ dt}$)
- **Mérés időtartama:** $2684.0\text{ ns}$ ($671\text{ dt}$)
- **Repetition delay (`rep_delay`):** $250.0\ \mu\text{s}$ (rögzített, megengedett tartomány: 0–2000 µs)
- **Kondicionáló ablak ($T_c$):** $16.128\ \mu\text{s}$ ($4032\text{ dt}$), slot-szinten párhuzamosítva a szomszéddal.
- **Pulzusszám ($N$):** 64
- **Pre-reset teljes ütemezett időtartam:** $\tau_{\max} + T_c = 64.0\ \mu\text{s} + 16.128\ \mu\text{s} = 80.128\ \mu\text{s}$ ($20032\text{ dt}$) — **mind a 4 karban és mind a 44 körben nanoszekundumos egyezéssel azonos!**
- **Valódi $\tau$ időzítés:**  
  A meghajtási ciklus utolsó $X$ kapuja és a reset közötti rés:  
  $t_{\text{gap}} = \text{félslot delay } (108\text{ ns}) + \tau$.  
  A legkisebb pontnál ($\tau = 8\text{ ns} = 2\text{ dt}$): $t_{\text{gap}} = 116\text{ ns}$ ($29\text{ dt}$).

---

## 4. Pilot Job Összetétele

1. **44 kampány áramkör:**
   - $D$ és $I$ karok: 4 $\tau$ ($8\text{ ns}, 4\ \mu\text{s}, 16\ \mu\text{s}, 64\ \mu\text{s}$) $\times$ 4 állapot ($G_0, G_T, E_0, E_T$) = 32 áramkör
   - Modell-ellenőrzés: $D$ és $I$ $\tau_0$-nál $t=2T$ késleltetéssel $\times$ 2 állapot ($G, E$) = 4 áramkör
   - Kontroll karok: $Nb$ és $D_{\text{fast}}$ $\tau_0$-nál $\times$ 4 állapot = 8 áramkör
2. **8 T1 kalibrációs áramkör:**
   - $t \in [0, 72, 144, 216, 288, 360, 432, 504]\ \mu\text{s}$
3. **Összesen:** 52 áramkör, 1000 lövés áramkörönként egyetlen összevont pilot jobban.

---

## 5. Lefagyasztott Kód és Manifest Hash-ek (FROZEN_SPEC v0.3)

| Komponens | Elérési Út | SHA256 Hash |
|---|---|---|
| Áramkörépítő | `src/circuit_builder.py` | `c458778b4bfad8396c69b0397db76f4c4dce8d56ce8675bb070f383cd0b01e12` |
| Fordítási és időzítés-audit | `src/audit_transpiler.py` | `4b763497c35544eb35f29ad59c102d90b540278ee999609f3e712380bcb7a64b` |
| Statisztikai elemző | `src/analysis.py` | `9213456b4379386fcb2c679d5d15a0ac9a50dfee50eace7feefe4e430f613a3f` |
| Validációs szimulátor | `src/simulator.py` | `0ebc12cc6b1000fb503a03dcbbc4d7b10d32e172141d5235dc8c7a588ef0e5f8` |
| Fail-closed beküldő | `src/pilot_runner.py` | `dba786be82eeb7e69b86e37ca080c6c75ee6acac30d9b1755f7837de279824ab` |
| Vakított pilot-elemző | `src/pilot_blind_analysis.py` | `7a96a40c1e0bff2ef707971e33fc19988e189fdf9977884c64881b7501f08033` |
| Auditált manifest | `prereg/manifest_audit.json` | `66076c14323ecf587a633eb8b1d85d7dfab2a92c6b07958a5f5e1492eda7f833` |
| Jóslati táblázat | `prereg/PREDICTIONS.md` | `8027e1c55b278b88bb22d22d33044c760a2f59eaeee59a6c87ed768a18a12101` |
