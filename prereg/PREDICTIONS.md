# PREDICTIONS.md — Háromoszlopos Jóslati Táblázat
**Kísérlet:** Qubit-előzményfüggés ("A Qubit Gumija")  
**Időbélyeg:** 2026-11-19T17:28:00Z (UTC)  
**Backend:** `ibm_marrakesh` (Heron r2) | $q=21$, $q'=20$  

---

## Előzetes Jóslati Mátrix

A megerősítő mérés beküldése előtt Máté oszlopába számszerű érték kerül (előjel, nagyság $\tau_0$-nál, és hogy csökken-e $\tau$-val).

| Mérőszám | Máté Irányhipotézise (H1) | Referencia (H0) | Ismert mechanizmusok (M) |
|---|---|---|---|
| **$L(\tau_0) = \ln(\Gamma_I/\Gamma_D)$** | $> 0$ (Becsült nagyságrend: $+0.08 \dots +0.15$) | $0$ | Bármelyik előjel: Gustavsson QP-pumpálás ($>0$), fűtés ($<0$), TLS-telítés ($>0$) |
| **$L(\tau)$ menete** | $\tau$-val csökken ($1/\tau$ vagy $\exp(-\tau/\tau_{\text{mem}})$ lecsengés) | Lapos $0$ | Mechanizmusfüggő visszaállási idő |
| **Szomszéd-meghajtás ($Nb$) vs $I$** | $\approx 0$ (Helyi hatás, nem globális chip-fűtés) | $0$ | $\neq 0$ melegedésnél vagy klaszter áthallásnál |
| **$D$ vs $D_{\text{fast}}$ (azonos kapuszám)** | $D > D_{\text{fast}}$ (A $|1\rangle$-ben töltött idő dominál) | $0$ | $\neq 0$, ha az excited állapotban leadott energia a kulcs |
| **Alapreferencia $P_G(0)$ (reset-maradék) $D$ vs $I$** | $\approx 0$ (A differenciáljel kiejti az additív hibát) | $0$ | $\neq 0$ tökéletlen resetnél vagy $|2\rangle$ szivárgásnál |

---

## Döntési Küszöbök
- Kétoldali szignifikanciaszint: $\alpha = 0.01$
- Ekvivalenciasáv (hatástalansági tartomány): $\delta_{\text{eq}} = 0.064$ (a pilot alapján finomítva)
- Megerősítő döntési kimenetelek: `ELOZMENY-LASSIT`, `ELOZMENY-GYORSIT`, `NULL`, `NEM DONTO`, `ERVENYTELEN`.
