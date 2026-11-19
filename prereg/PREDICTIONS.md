# PREDICTIONS.md — Végleges Háromoszlopos Jóslati Táblázat
**Kísérlet:** Qubit-előzményfüggés ("A Qubit Gumija")  
**Időbélyeg:** 2026-11-19T18:35:00Z (UTC)  
**Backend:** `ibm_marrakesh` (Heron r2) | $q=21$, $q'=20$  
**Pilot empirikus $T_1$:** $219.39 \pm 9.32\ \mu\text{s}$  
**Kalibrált kiolvasási késleltetés:** $T = 220.0\ \mu\text{s}$, modell-ellenőrzés: $2T = 440.0\ \mu\text{s}$  

---

## 1. Megerősítő Jóslati Mátrix

| Mérőszám | Máté Irányhipotézise (H1) | Referencia (H0) | Ismert mechanizmusok (M) |
|---|---|---|---|
| **$L(\tau_0) = \ln(\Gamma_I/\Gamma_D)$** | **$+0.10$** ($+10.5\%$ relatív $T_1$ növekedés $\tau_0=116\text{ ns}$-nál) | $0$ | Gustavsson QP-pumpálás ($>0$), fűtés ($<0$), TLS-telítés ($>0$) |
| **$L(\tau)$ menete** | $\tau_{\text{mem}} = 16.0\ \mu\text{s}$ időállandóval csökken: $L(4\ \mu\text{s})=+0.078$, $L(16\ \mu\text{s})=+0.037$, $L(64\ \mu\text{s})=+0.002$ | Lapos $0$ | Környezeti relaxációs időtől függő lecsengés |
| **Szomszéd-meghajtás ($Nb$) vs $I$** | $0 \pm 0.01$ (Helyi kvantumhatás, nem chip-szintű fűtés) | $0$ | $\neq 0$ áthallásnál vagy globális melegedésnél |
| **$D$ vs $D_{\text{fast}}$ (azonos kapuszám)** | $L_D - L_{D_{\text{fast}}} \ge +0.05$ (A gerjesztett $|1\rangle$ állapotban töltött idő a domináns) | $0$ | $\approx 0$, ha a puszta kapuimpulzusok száma számít |
| **Alapreferencia $P_G(0)$ (reset-maradék) $D$ vs $I$** | $|P_G^D(0) - P_G^I(0)| \le 0.005$ | $0$ | $\neq 0$ tökéletlen resetnél vagy $|2\rangle$ szivárgásnál |

---

## 2. Előregisztrált Döntési Küszöbök
- **Szignifikanciaszint:** kétoldali $\alpha = 0.01$ (egymintás t-próba a legalább 6 érvényes blokk $L(\tau_0)$ értékein).
- **Ekvivalenciasáv (hatástalanság):** $\delta_{\text{eq}} = 0.064$ (a $99\%$-os konfidenciaintervallum teljes beágyazódása $\pm \delta_{\text{eq}}$-be).
- **Érvényességi kapuk blokkonként (Section 11):**
  - Minimális kontraszt: $S(0) = P_E(0) - P_G(0) \ge 0.85$ mindkét karban.
  - Maximális alapzaj: $P_G(0) \le 0.03$ mindkét karban.
  - Modell-ellenőrzés: $|S(2T) - S(T)^2 / S(0)| \le 2.576 \times \text{SE}$.
