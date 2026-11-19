# Megerősítő Előregisztráció (Confirmatory Pre-Registration v1.0)
**Kísérlet:** Qubit-előzményfüggés ("A Qubit Gumija")  
**Készült:** 2026-11-19T18:45:00Z (UTC)  
**Backend:** `ibm_marrakesh` (Heron r2 processzor, 156 fizikai qubit)  
**Mért Qubitpár:** Elsődleges $q=21$, Szomszéd $q'=20$  
**Pilot Eredmény:** $T_1 = 219.39 \pm 9.32\ \mu\text{s}$, $S(0) = 0.9891$, $P_G(0) = 0.0013$  

---

## 1. Kalibrált Kísérleti Paraméterek

A pilot mérés empirikus adatai alapján rögzített értékek:
- **Kiolvasási késleltetés ($T$):** $T = 220.0\ \mu\text{s}$ ($55\,000\text{ dt}$), pontosan igazítva a mért $T_1$-hez.
- **Modell-ellenőrzési késleltetés ($2T$):** $2T = 440.0\ \mu\text{s}$ ($110\,000\text{ dt}$).
- **Pre-reset teljes ütemezett idő:** $\tau_{\max} + T_c = 64.0\ \mu\text{s} + 16.128\ \mu\text{s} = 80.128\ \mu\text{s}$ ($20\,032\text{ dt}$) minden áramkörben.
- **Valódi legkisebb rés ($\tau_0$):** $t_{\text{gap}} = 108\text{ ns (félslot)} + 8\text{ ns (delay)} = 116\text{ ns}$ ($29\text{ dt}$).
- **Repetition delay:** `rep_delay` = $250.0\ \mu\text{s}$ (rögzített).
- **Integritási opciók:** `init_qubits = True`, dynamical decoupling = False, twirling = False.

---

## 2. Előre Rögzített Hipotézis és Számszerű Jóslat

- **Máté iránya (H1):** $L(\tau_0) = \ln(\Gamma_I / \Gamma_D) = \mathbf{+0.10}$ ($\approx +10.5\%$ relaxációs időtartam-növekedés a periodikusan meghajtott qubiten).
- **Memória lecsengés:** $L(\tau) = L(\tau_0) \exp(-\tau / \tau_{\text{mem}})$ ahol $\tau_{\text{mem}} = 16.0\ \mu\text{s}$ (a meghajtási ablak $T_c$ idejével egyező relaxációs skála).
- **Referencia (H0):** $L(\tau) = 0$ minden $\tau$-ra (előzményfüggetlen markovi viselkedés).
- **Ismert mechanizmusok (M):** Kvázirészecske-pumpálás ($>0$), fűtés ($<0$), TLS-telítés ($>0$).

---

## 3. Statisztikai Döntési Szabályzat és Küszöbök

- **Szignifikanciaszint:** Kétoldali $\alpha = 0.01$ egymintás t-próba a blokkok $L(\tau_0)$ értékein (legalább 6 érvényes blokk).
- **Ekvivalenciasáv:** $\delta_{\text{eq}} = 0.075$ (a $99\%$-os konfidenciaintervallum beágyazódása a hatástalansági sávba).
- **Érvényességi Kapuk (Section 11):**
  - Minimális kezdeti kontraszt blokkonként: $S(0) = P_E(0) - P_G(0) \ge 0.85$.
  - Maximális reset-maradék blokkonként: $P_G(0) \le 0.03$.
  - Modell-ellenőrzés: $|S(2T) - S(T)^2 / S(0)| \le 2.576 \times \text{SE}$.
- **Ítéleti Kategóriák:**
  - `ELOZMENY-LASSIT`: $p < 0.01$ és $\bar{L} > 0$, modell-ellenőrzés sikeres.
  - `ELOZMENY-GYORSIT`: $p < 0.01$ és $\bar{L} < 0$, modell-ellenőrzés sikeres.
  - `NULL`: A $99\%$-os konfidenciaintervallum teljes terjedelmében a $[-\delta_{\text{eq}}, +\delta_{\text{eq}}]$ sávon belül van.
  - `NEM DONTO`: Egyik feltétel sem teljesül.
  - `ERVENYTELEN`: 6-nál kevesebb érvényes blokk, kapuhullás, vagy szignifikáns modell-hiba.

---

## 4. Vakítási Rendszer (Blinding Gate)

- A kondicionáló karok véletlenszerű fedőneveket kapnak (`Alpha`, `Beta`, `Gamma`, `Delta`).
- A hozzárendelést tartalmazó kulcsfájl (`data/blind_mapping.json`) a repozitóriumban `.gitignore` alatt áll, privát és rejtett.
- **Lefagyasztott Vakítási Kulcs Hash (SHA256):**  
  `7d7fe12284c746563e5d17d4f23e00d65bc95e74b075383624a0e5b6389ba2e6`
- A kulcs megnyitása kizárólag a megerősítő jobok lefutása és az érvényességi kapuk ellenőrzése után engedélyezett.

---

## 5. Lefagyasztott Kód- és Manifest Hash-ek (FROZEN_SPEC v1.0)

| Komponens | Elérési Út | SHA256 Hash |
|---|---|---|
| Áramkörépítő | `src/circuit_builder.py` | `47a5f5d7bc6aa2fafa1565bbd175ae8240e13d50f5889846131c4377a1c2be4c` |
| Fordítási audit | `src/audit_transpiler.py` | `4b763497c35544eb35f29ad59c102d90b540278ee999609f3e712380bcb7a64b` |
| Statisztikai elemző | `src/analysis.py` | `35cab983c6b6d92652b77e776c7514d566c791e548765579b1306364a4fe7eb8` |
| Validációs szimulátor | `src/simulator.py` | `3756d879b65e63793d8f19d7117e92aba3e9b8419cafc13c2dded05880da46c9` |
| Fail-closed beküldő | `src/pilot_runner.py` | `dba786be82eeb7e69b86e37ca080c6c75ee6acac30d9b1755f7837de279824ab` |
| Vakított pilot-elemző | `src/pilot_blind_analysis.py` | `7a96a40c1e0bff2ef707971e33fc19988e189fdf9977884c64881b7501f08033` |
| Auditált manifest | `prereg/manifest_audit.json` | `dd01de597dc1fad33d9c419c7c357957f26f5146e001cb646e5e526d531d9809` |
| Jóslati táblázat | `prereg/PREDICTIONS.md` | `de189b54c6aed0bfff17b93cb28ce64638a2656349e72882a523322e90301c01` |
