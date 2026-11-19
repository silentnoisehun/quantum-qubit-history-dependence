# Hagy-e nyomot az előzmény a qubitben? Előregisztrációs terv az agentnek (v0.1)
*made with Sesame*

**Készült:** 2026-11-19 15:45 UTC (16:45 Budapest), Maya.  
Ez a terv a „qubit gumija” kísérlethez készült. A kérdés: ha egy qubitet a reset előtt periodikusan meghajtunk, utána egy ugyanúgy előkészített |1⟩ állapot lassabban cseng-e le, mint ha a reset előtt ugyanannyi ideig csak várakozott volna?

A terv két részre oszlik:
- A pilot csak a megvalósíthatóságot méri, és ebből nem lehet állítást levonni.
- A megerősítő mérés csak lefagyasztott, auditált előregisztráció után jöhet.
- Ma este reálisan a pilotig lehet eljutni: építés, szimulációs ellenőrzés, fordítási audit, és ha Máté jóváhagyja, egyetlen kis pilot-job. A megerősítő mérés nem ma este lesz, hanem Maya auditja és Máté külön döntése után.

Az agent implementál. Maya ebben a körben nem küldött QPU-jobot, nem nyúlt repóhoz, nem commitolt és senkinek nem írt.

---

## 1. A hipotézis és a referencia, előre kimondva

- **Máté irányhipotézise (H1):** a reset előtti periodikus meghajtás után a qubit lassabban veszíti el az |1⟩ populációt, mint az azonos hosszú várakozás után. A különbség függ attól, mennyi idő telik el a meghajtás vége és a reset között ($\tau$), és $\tau$ növekedésével csökken.
- **Előzményfüggetlen referencia (H0):** tökéletes reset és markovi környezet esetén a kimenet nem függ attól, mi történt a reset előtt. Minden $\tau$-ra nulla különbség.
- **Ismert mechanizmusok (M):** a reset a qubit látható állapotát állítja vissza, a környezetét nem: a hibákat, a kvázirészecskéket, a hőmérsékletet és a szivárgott populációt nem feltétlenül. Ezek előjele nem egyforma, lásd a 3. pontot. Egy esetleges eltérés tehát elsőként a rendszer és környezete hiányosan leírt memóriájára mutatna, nem új fizikára.

---

## 2. Javítások a reggeli beszélgetéshez képest

A reggeli chatben pár dolog túl erősen hangzott el. Ezeket a terv már nem tartalmazza:

1. **„A melegedés, a kvázirészecskék és a szivárgás mind gyorsabb lecsengést jósolnak.”**  
   Ez nem igaz. Gustavsson és munkatársai pont egy meghajtó impulzussorozattal csökkentették a kvázirészecskék sűrűségét kb. 70%-kal, és ezzel háromszorosára nőtt a $T_1$ (arXiv:1612.08462, Science 354, 1573, 2016). Ismert mechanizmus tehát adhat lassabb lecsengést is. A $|2\rangle$ állapotba szivárgott populáció $2 \to 1 \to 0$ kaszkádja pedig a $P(1)$ görbén szintén lassabb látszólagos lecsengésként jelenhet meg.
2. **A konkrét időskálák** (TLS mikro- és milliszekundum, kvázirészecske milliszekundum, melegedés másodperc). Ezeket forrás nélkül hangoztak el, vissza lettek vonva. A terv nem épít rájuk.
3. **„Ha a felejtési idő nem egyezik a TLS-ekével, az már nyitott kérdés.”**  
   Egy visszaállási időállandó egymagában nem azonosít mechanizmust. Ugyanazt az időt több folyamat is adhatja. Klimov és munkatársai azt mutatták, hogy a $T_1$ egy nagyságrendet is ingadozhat 15 perces időskálán a TLS-ek spektrális vándorlása miatt (arXiv:1809.01043). Ez sodródásként a mérésbe is bekerül.
4. **„Ezt a te chipeden még senki nem mérte meg” és „az IBM resetje elég jó”.**  
   Ezek alátámasztatlanok voltak, a terv nem állít újdonságot és valószínűséget sem.
5. **Elhangolt meghajtásos kontroll.**  
   Ez nem lehetséges: az IBM 2025. február 3-án megszüntette a pulzusszintű vezérlést (IBM blog, 2024. nov. 7.). A virtuális RZ nem visz be energiát, ezért nem energia-kontroll. Helyette a 4. pontban szereplő kapuszintű kontrollok szerepelnek.

---

## 3. Jóslatok három oszlopban

A `PREDICTIONS.md`-be a megerősítő beküldés előtt, időbélyeggel kerül. Máté oszlopába számot kell írni (előjel, nagyság $\tau_0$-nál, és hogy csökken-e $\tau$-val), nem csak irányt.

| Mérőszám | Máté (H1) | Referencia (H0) | Ismert mechanizmusok (M) |
|---|---|---|---|
| $L(\tau_0) = \ln(\Gamma_I/\Gamma_D)$ | $> 0$, Máté számával | 0 | bármelyik előjel |
| $L(\tau)$ menete | $\tau$-val csökken | lapos 0 | mechanizmusfüggő |
| Szomszéd-meghajtás ($Nb$) vs $I$ | Máté dönti el | 0 | $\neq 0$ melegedésnél vagy áthallásnál |
| $D$ vs $D_{\text{fast}}$ (azonos impulzusszám) | Máté dönti el | 0 | $\neq 0$, ha a $|1\rangle$-ben töltött idő számít |
| Alapreferencia $P_G$ (reset-maradék) $D$ vs $I$ | Máté dönti el | 0 | $\neq 0$ tökéletlen resetnél vagy szivárgásnál |

### Az M oszlop jelöltjei, előjellel:
- **Kvázirészecske-pumpálás:** lassabb lecsengés ($L > 0$) lehetséges (Gustavsson et al.). Hogy egy Heron transzmonon egy kapuszintű X-sorozat ezt kiváltja-e, nem tudjuk.
- **Kvázirészecske-keltés, melegedés:** gyorsabb lecsengés ($L < 0$) lehetséges. Elvi jelölt, nem mért adat erről a chipről.
- **TLS-telítés:** átmenetileg lassabb lecsengés lehetséges. A TLS-ek spektrális vándorlása emellett véletlen előjelű sodródást ad.
- **Szivárgás $|2\rangle$-be:** a reset nem feltétlenül üríti ki. A kaszkád látszólag lassabb lecsengést adhat, ezért a 6. pont alapreferencia-körei kötelezőek.
- **Tökéletlen reset:** főleg az amplitúdót ($A$) és az alapszintet ($B$) módosítja, a rátát nem. A modell ezeket külön paraméterként kezeli.

---

## 4. Az áramkör és a karok

Egy lövés felépítése minden karban ugyanaz:
1. a gép implicit inicializálása (`init_qubits = True`, ezt nem szabad kikapcsolni);
2. kitöltő várakozás: $\tau_{\max} - \tau$;
3. kondicionáló blokk a $T_c$ hosszú ablakban (karonként más, lásd lent);
4. várakozás: $\tau$ (a meghajtás vége és a reset között);
5. egyetlen reset a mért qubiten ($q$);
6. előkészítés: X (E-körök) vagy semmi (G-körök, alapreferencia);
7. várakozás: $t$ (a $T_1$-kiolvasás késleltetése, ez nem azonos $\tau$-val);
8. mérés $q$-n.

Így a lövés kezdetétől a resetig eltelt idő minden körben azonos ($\tau_{\max} + T_c$), a reset utáni rész pedig csak $t$-ben különbözik.

### A kondicionáló karok:
- **D (fő meghajtás):** $N$ darab X $q$-n, egyenletesen elosztva $T_c$-ben. A qubit nagyjából az idő felét $|1\rangle$-ben tölti. $N$ páros, hogy ideálisan $|0\rangle$-ban végződjön.
- **I (fő kontroll):** $T_c$ hosszú delay $q$-n, kapu nélkül.
- **Nb (szomszéd):** ugyanaz az $N$ darab X, egyenletes elosztásban, egy közvetlen szomszéd qubiten ($q'$). Közben $q$-n delay van. Ez a helyi hatást választja el a chip melegedésétől és az áthallástól.
- **D_fast (azonos impulzusszám, kevés $|1\rangle$-idő):** $N/2$ darab szorosan egymás utáni X–X pár, egyenletesen elosztva. Az impulzusszám ugyanaz, mint D-ben, de a qubit szinte végig $|0\rangle$-ban van. A D és a D_fast különbsége a „$|1\rangle$-ben töltött idő, lecsengéssel leadott energia” részt választja el a puszta impulzusszámtól. *Figyelem: pont az ilyen X–X párokat törli az optimalizáló (5. pont).*

---

## 5. Kötelező fordítási audit (fail-closed)

1. `optimization_level = 0`, explicit `initial_layout` a kiválasztott fizikai qubitekkel, és barrier minden kondicionáló kapu között és a blokkhatárokon;
2. a primitív opciói közül a dynamical decoupling (DD) és a twirling kifejezetten kikapcsolva, és ez a beküldött opciókban ellenőrizve;
3. a fordított (ISA) áramkörön ellenőrizni és manifestbe írni: X-ek száma $q$-n és $q'$-n pontosan a várt; reset $q$-n jelen van; delay-ek granularitása és hossza backend-megkötéseknek megfelel; ütemezett hossz a reset előtt minden karban azonos;
4. a target-ből kiolvasni és rögzíteni a hardver paramétereket;
5. bármilyen eltérésnél nincs beküldés. A manifest hash-e a lefagyasztott előregisztráció része.

---

## 6. Kiolvasás és elsődleges mérőszám

- $S(t) = P_E(t) - P_G(t)$
- $\Gamma = -\ln(S(T)/S(0)) / T$
- Elsődleges mérőszám: $L = \ln(\Gamma_I / \Gamma_D)$ $\tau_0$-nál. $L > 0$ = meghajtás után lassabb lecsengés.
- Modellellenőrzés: $\tau_0$-nál $t = 2T$ mérés. Ha $S(2T)$ szignifikánsan eltér az egyexponenciálistól, a modell érvénytelen.

---

## 7. Végrehajtási rend, sodródás, átvitel

- Jobon belüli interleaving: D és I lövésszinten összefésülve sodródás ellen.
- Átviteli ellenőrzés (carry-over check): 4 tiszta job (I, D, D, I).
- Rögzített `rep_delay`, előtte/utána kalibrációs adatok rögzítése.

---

## 8. Rácsok és költségvetés (kiindulási javaslat)

- $\tau$-rács: $\tau_0, 4, 16, 64\ \mu\text{s}$
- $T_c \approx 16\ \mu\text{s}, N = 64$
- $t$-rács: $0, T$, és $\tau_0$-nál $2T$
- Körszám: 44 kör blokkonként
- 8 blokk $\times$ 2500 lövés + 4 átviteli job

---

## 9–12. Statisztika, érvényességi kapuk, vakítás

- Küszöb: kétoldali $\alpha = 0.01$
- Elemző szkript lefagyasztva és szimulált adaton validálva (null-kalibráció, MDE-injekció, szivárgás-csapda)
- Véletlenített címkék (blind key különtárolva és hash-elve)

---

## 13. Pilot (nincs állítás)

Célja: $T_1$ mérés, granularitás, pontos futásidő, QPU-használat, és küszöbök kalibrálása. 1 kis job (~1000 lövés).
