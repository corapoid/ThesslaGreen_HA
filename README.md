<!-- Badges: start -->
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5?style=for-the-badge&logo=homeassistantcommunitystore&logoColor=white)](https://hacs.xyz/)
[![GitHub - Downloads](https://img.shields.io/github/downloads/aLAN-LDZ/ThesslaGreen_HA/total?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/releases)
[![Issues & PRs](https://img.shields.io/github/issues-pr/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/issues)
[![Latest Release](https://img.shields.io/github/v/release/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/releases)
[![Release Date](https://img.shields.io/github/release-date/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge&label=Latest%20Release)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/releases)
[![Pre-Release Date](https://img.shields.io/github/release-date-pre/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge&label=Latest%20Beta%20Release)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/releases)

[![Stars](https://img.shields.io/github/stars/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/stargazers)
[![Forks](https://img.shields.io/github/forks/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/network/members)
[![Last Commit](https://img.shields.io/github/last-commit/aLAN-LDZ/ThesslaGreen_HA?style=for-the-badge)](https://github.com/aLAN-LDZ/ThesslaGreen_HA/commits)

# ThesslaGreen_HA

**Dokumentacja / Documentation:** [Polski](#-integracja-home-assistant-dla-rekuperatorów-thessla-green-z-komunikacją-modbus-tcp)
· [English](#-thesslagreen_ha--home-assistant-integration-for-thessla-green-heat-recovery-units)
· [Changelog](CHANGELOG.md)

## 🇵🇱 Integracja Home Assistant dla rekuperatorów Thessla Green z komunikacją Modbus TCP

> 🛠️ Projekt rozwijany. Nowe profile opisane poniżej należą do zmian **Unreleased**
> w [changelogu](CHANGELOG.md). Testy automatyczne obejmują protokół Modbus i API HA;
> weryfikacja na fizycznych urządzeniach pozostaje do wykonania.

### Obsługiwane profile

| Wybór w konfiguracji | Domyślny slave ID | Zakres |
| --- | --- | --- |
| **AirPack4 300h** | 10 | Funkcje użytkownika opisane dla sterownika 4.89 i TG-02 0.30, harmonogramy i diagnostyka |
| **Particle+** | 30 | Particle+500: pomiary pyłu, filtry, sterowanie i alarmy; rozszerzona tabela alarmów od firmware 3.4.0 |
| **Rekuperator — profil ogólny** | 10 | Dotychczasowa mapa integracji; zachowana dla istniejących wpisów |

Wymagania: **Home Assistant ≥ 2025.10.0**, bramka **Modbus TCP → RTU**
i prawidłowo ustawiony adres slave. Port TCP zależy od bramki; wartość **8899**
w formularzu jest domyślna. Parametry RTU według protokołów producenta: **9600 bps, 8N1**.

### ✨ Funkcje

- Komunikacja z rekuperatorem Thessla Green przez **Modbus TCP**
- Odczyty i sterowanie dopasowane do profilu urządzenia:
  - `sensor` — temperatury, przepływy powietrza, statusy, błędy
  - `binary_sensor` — stany pracy (także przez `coils`), siłowniki bypassu, alarmy
  - `switch` — bypass, on/off, zmiana trybu
  - `select` — wybór trybu pracy i sezonu (lato/zima)
  - `number` — intensywność manualna (10–100%) i nastawy funkcji dodatkowych
  - `time`, `button`, `text` — harmonogramy, procedury filtrów i nazwa sterownika AirPack4
- Obsługa stanów w czasie rzeczywistym z szybkim odświeżaniem (domyślnie co 30s, konfigurowalne)
- Wykrywanie utraty komunikacji oraz automatyczne ponawianie konfiguracji przy starcie
- Konfiguracja przez interfejs użytkownika (UI Config Flow)
- Integracja automatycznie grupuje wszystkie encje pod jedno urządzenie w Home Assistant
- Wsparcie dla HACS (Home Assistant Community Store)
- Obliczane sprawność i moc odzysku; COP po wskazaniu encji mocy chwilowej w W/kW

---

### 📦 Instalacja

#### Przez HACS

1. Dodaj to repozytorium jako **Custom Repository** w HACS
2. Zainstaluj integrację **Thessla Green**
3. Zrestartuj Home Assistant
4. Przejdź do `Ustawienia → Integracje → Dodaj integrację`
5. Wybierz **Thessla Green** i skonfiguruj IP urządzenia, port oraz numer slave

#### Aktualizacja istniejącej instalacji

1. Zaktualizuj integrację w HACS lub skopiuj nowy katalog `thessla_green`.
2. Zrestartuj Home Assistant.
3. Dla **AirPack4 300h** wybierz model i system kontroli filtrów w opcjach
   istniejącego wpisu. Zapis automatycznie przeładuje integrację.
4. Włącz potrzebne encje harmonogramów i szczegółowej diagnostyki na karcie urządzenia.
5. Particle+ dodaj jako osobny wpis integracji z jego własnym slave ID.

#### Ręcznie

1. Pobierz lub sklonuj repozytorium:
    ```bash
    git clone https://github.com/aLAN-LDZ/ThesslaGreen_HA.git
    ```
2. Skopiuj katalog `ThesslaGreen_HA/custom_components/thessla_green` do
   `<katalog konfiguracji HA>/custom_components/thessla_green`.
3. Zrestartuj Home Assistant i dodaj integrację jak powyżej.

Wymagana wersja Home Assistant: **2025.10.0 lub nowsza**.
Opcjonalny sensor COP musi podawać moc chwilową w **W lub kW**, nie energię w Wh/kWh.
Zmiana lub usunięcie sensora w opcjach automatycznie przeładowuje integrację.
Po nieudanym połączeniu przy uruchomieniu HA ponawia konfigurację automatycznie.

---

### AirPack4 300h — sterownik 4.89, TG-02 0.30

**Istniejąca instalacja:** po aktualizacji i restarcie HA otwórz opcje integracji,
ustaw **Model rekuperatora → AirPack4 300h** i zapisz. Integracja przeładuje się
automatycznie. Przy nowej instalacji wybierz **AirPack4 300h** w pierwszym kroku.
Domyślny slave ID to **10**; host i port muszą odpowiadać bramce Modbus TCP.

Na karcie urządzenia oraz w sensorach diagnostycznych dostępne są **model,
numer seryjny, rzeczywista wersja sterownika i wersja TG-02**. Wersje są odczytywane
z urządzenia, a nie wpisywane na stałe jako 4.89/0.30.

Profil udostępnia:
- tryb automatyczny, manualny i chwilowy, sezon lato/zima oraz funkcje specjalne;
- intensywność manualną i chwilową, temperatury zadane KOMFORT **10–45°C co 0,5°C**;
- FPX OFF/FPX1/FPX2, działanie ERV, faktyczny status bypassu i potwierdzenie pracy O1;
- progi i tryby bypassu, różnicowanie strumieni oraz intensywność z trybu pracy;
- GWC: zezwolenie, progi, regenerację dobową/temperaturową i godziny regeneracji;
- intensywności, czasy i opóźnienia wietrzenia, kominka, okapu i pustego domu;
- nastawy biegów AirS, język Air++ i edytowalną nazwę urządzenia w sterowniku;
- temperatury, przepływy, intensywności, zużycie/terminy filtrów i szczegółowe alarmy;
- kontrolę filtrów, potwierdzenie wymiany odpowiednich filtrów oraz resety alarmów
  oznaczonych przez producenta jako resetowalne przez użytkownika;
- obliczane sprawność, moc odzysku i COP z opcjonalnym sensorem mocy W/kW.

**Harmonogramy:** każdy dzień lata i zimy ma cztery odcinki, z encjami godziny
rozpoczęcia, intensywności, temperatury i aktywacji odcinka. Osobne encje sterują
wietrzeniem według harmonogramu oraz w trybie manualnym. Encje harmonogramów
i szczegółowych wejść/alarmów są domyślnie wyłączone w rejestrze HA — włącz
potrzebne na karcie urządzenia w ustawieniach encji. Godziny mają rozdzielczość
jednej minuty. Ustawienie godziny aktywuje odcinek; wyłączenie zapisuje właściwy
znacznik protokołu. Po ponownym włączeniu używana jest zapamiętana godzina,
a po przeładowaniu integracji dla wyłączonego odcinka — godzina domyślna.
Harmonogram jest odczytywany co **5 minut** i ponownie po zapisie z HA;
zmiany dokonane na panelu mogą być widoczne z takim opóźnieniem.

**Filtry:** w opcjach wskaż zainstalowany system: bez AFC, AFC nawiewu,
AFC wywiewu lub AFC obu filtrów. Dopóki system jest nieokreślony, przyciski
potwierdzania wymiany są niedostępne. Dla filtra kontrolowanego przez AFC
nie wysyła się polecenia potwierdzania wymiany przeznaczonego dla filtra bez AFC.

Nieobsługiwane rejestry opcjonalnego wyposażenia są pomijane wyłącznie po
odpowiedzi Modbus **Illegal Data Address**; timeouty i awarie urządzenia powodują
niedostępność encji. Brak temperatury `0x8000` i brak przepływu CF `0xFFFF`
nie są publikowane jako ujemne pomiary ani używane w obliczeniach.
Profil obejmuje funkcje użytkownika opisane w
[protokole AirPack4](https://thesslagreen.com/wp-content/uploads/MODBUS_USER_AirPack_4_10.2022.01.pdf);
nie udostępnia kalibracji instalatora, klucza produktu ani zmiany parametrów portów Modbus.

---

### Particle+500 — osobny adres Modbus

Dodaj kolejny wpis integracji **Thessla Green**, wybierz **Particle+** i podaj
adres IP oraz port bramki **Modbus TCP → RTU**, a także adres slave oczyszczacza
(domyślnie **30**). Parametry strony RTU według producenta: **9600 bps, 8N1**.
Port TCP zależy od bramki; domyślne 8899 należy zmienić, jeśli używa innego portu.
Bramka musi obsługiwać ramki Modbus TCP, nie tylko przesyłać surowe ramki RTU przez TCP.
Istniejące wpisy integracji są traktowane jako rekuperatory.

Obsługiwane encje Particle+:
- stężenie pyłu z czujników **PmSensor OUT / IN**, z atrybutem `particle_type`;
- spadek ciśnienia i zużycie filtra wstępnego oraz HEPA;
- intensywność filtracji automatycznej i obliczona nastawa stężenia pyłu;
- wstrzymanie filtracji, alarm zbiorczy, awaria wentylatora/czujników pyłu oraz wymiana filtrów;
- dla firmware **3.4.0+** także brak zezwolenia na pracę, brak filtra wstępnego
  i brak filtra HEPA; alarm zbiorczy obejmuje obie tabele alarmów;
- zasilanie, tryb manualny/automatyczny, wybór PM10/PM2.5 i sposobu regulacji;
- intensywność manualna **10–100%**, nastawa bezwzględna **0–200 µg/m³**
  i stężenia odniesienia PM10/PM2.5 **10–300 µg/m³**.

W trybie względnym procentowa nastawa pozostaje ustawieniem panelu urządzenia.
Czujniki pyłu pokazują **wybrany** rodzaj pyłu, a nie oba rodzaje jednocześnie;
według protokołu domyślna częstotliwość pomiarów wynosi 10 s w trybie automatycznym
i 30 minut w trybie manualnym lub przy wyłączonym oczyszczaczu.
Tryb automatyczny może być niedostępny przy awarii PmSensor OUT.
Błąd komunikacji oznacza niedostępność encji, a błędy zapisu są zgłaszane w HA.

Mapa rejestrów: [protokół producenta Particle+](https://thesslagreen.com/wp-content/uploads/MODBUS_USER_Particle_08.2021.01.pdf).
Odczyty używają funkcji 03 i nie przekraczają 16 rejestrów na żądanie.

---

## 🇬🇧 ThesslaGreen_HA – Home Assistant integration for Thessla Green heat recovery units

> 🛠️ Under development. The new profiles below are **Unreleased** changes listed
> in the [changelog](CHANGELOG.md). Automated checks cover Modbus and HA APIs;
> physical-device verification is pending.

### Supported profiles

| Configuration choice | Default slave ID | Scope |
| --- | --- | --- |
| **AirPack4 300h** | 10 | Documented user functions for controller 4.89 / TG-02 0.30, schedules and diagnostics |
| **Particle+** | 30 | Particle+500 dust measurements, filters, controls and alarms; extended alarms from firmware 3.4.0 |
| **Rekuperator — profil ogólny** | 10 | Existing integration register map retained for legacy entries |

Requirements: **Home Assistant ≥ 2025.10.0**, a **Modbus TCP → RTU** gateway,
and the correct slave ID. Set the TCP port to match the gateway; **8899** is the
form default. Manufacturer RTU defaults: **9600 bps, 8N1**.

### ✨ Features

- Communicates with Thessla Green units over **Modbus TCP**
- Device-profile-specific readings and controls:
  - `sensor` — temperatures, airflow, statuses, errors
  - `binary_sensor` — state confirmations (via coils), bypass actuator, alarms
  - `switch` — bypass, on/off, mode change
  - `select` — operation modes and season (summer/winter)
  - `number` — manual intensity (10–100%) and additional function settings
  - `time`, `button`, `text` — AirPack4 schedules, filter procedures and controller name
- Real-time updates with fast polling (default 30s, configurable)
- Robust error handling and reconnection logic
- Easy setup via Home Assistant UI (Config Flow)
- All entities grouped into a single device in Home Assistant
- Fully HACS-compatible (Home Assistant Community Store)
- Calculated efficiency and recovery power; COP with an external instantaneous-power sensor in W/kW

---

### 📦 Installation

#### Using HACS

1. Add this repository as a **Custom Repository** in HACS
2. Install **Thessla Green** integration
3. Restart Home Assistant
4. Go to `Settings → Integrations → Add Integration`
5. Select **Thessla Green** and configure IP address, port, and slave ID

#### Upgrading an existing installation

1. Update through HACS or replace the `thessla_green` integration directory.
2. Restart Home Assistant.
3. For **AirPack4 300h**, select the model and installed filter-monitoring system
   in the existing entry's options. Saving automatically reloads the entry.
4. Enable the desired schedule/detailed-diagnostic entities from the device page.
5. Add Particle+ as a separate integration entry with its own slave ID.

#### Manual Installation

1. Download or clone the repository:
    ```bash
    git clone https://github.com/aLAN-LDZ/ThesslaGreen_HA.git
    ```
2. Copy `ThesslaGreen_HA/custom_components/thessla_green` into
   `<HA configuration directory>/custom_components/thessla_green`.
3. Restart Home Assistant and add the integration as described above.

Requires **Home Assistant 2025.10.0 or newer**. The optional COP sensor must
report instantaneous power in **W or kW**, not energy in Wh/kWh. Changing or
clearing it in options automatically reloads the integration. Home Assistant
automatically retries setup if the device is unavailable at startup.

### AirPack4 300h — controller 4.89, TG-02 0.30

For an existing installation, select **AirPack4 300h** as the recuperator model
in integration options; saving reloads the entry. For a new installation,
select this model in the first configuration step. Default slave ID: **10**.
The device page and diagnostic sensors report the actual model, serial number,
controller firmware and TG-02 firmware read from the device.

Controls cover automatic/manual/temporary operation, seasons and special
functions, manual and temporary intensity/temperature, EKO/KOMFORT, ERV,
bypass and GWC settings/regeneration, airing/fireplace/hood/empty-house
parameters, AirS speeds, Air++ language and the controller name. Filter wear,
replacement dates, sensor/output states and detailed alarms are available.
Filter-check procedures and documented user alarm resets have buttons.

Summer/winter schedules expose four periods per day, with start-time, intensity,
temperature and enable controls. Scheduled/manual airing has separate clock
controls. Schedule entities and detailed input/alarm entities are disabled by
default in HA; enable the desired entities from the device page. Clocks have
minute precision; setting a time enables the corresponding period. Enabling a
disabled period restores its remembered clock, or a default after entry reload.
Schedules are polled every five minutes and invalidated after HA writes.
Temporary-mode fields use one FC16 transaction; packed schedule fields use a
serialized read-modify-write to preserve the other value.

Select the installed filter-monitoring system in options. Replacement-confirmation
buttons only apply to filters without AFC monitoring and remain unavailable while
the system is unspecified. Only explicit Illegal Data Address responses suppress
unsupported optional registers. Other failures make entities unavailable.
Missing-temperature/CF sentinel values are not used as measurements or in COP.
The profile implements documented user functions rather than installer calibration,
product-key programming or Modbus-port configuration.

### Particle+500 — separate Modbus address

Add another **Thessla Green** integration entry, select **Particle+**, and enter
the **Modbus TCP → RTU** gateway host/port and the purifier's slave ID (default **30**).
The manufacturer's default RTU settings are **9600 bps, 8N1**. Set the TCP port
to match your gateway. Raw RTU-over-TCP gateways are not supported.
Existing entries continue to use the recuperator profile.

Particle+ provides OUT/IN dust concentration with a `particle_type` attribute,
filter pressure drops and wear, automatic fan intensity and calculated target,
filtration-blocked status, alarm/fan/dust-sensor faults and filter replacement alerts.
Firmware **3.4.0+** additionally exposes missing work permission, prefilter and
HEPA-filter alarms; the combined alarm includes both alarm tables. Older firmware
is not queried for the extended alarm register.
Controls include power, manual/automatic mode, PM10/PM2.5 selection, regulation mode,
manual intensity (10–100%), absolute dust target (0–200 µg/m³), and reference
concentrations (10–300 µg/m³). Set the relative percentage target on the device panel.
Dust sensors report the selected particle type; default measurement intervals are
10 seconds in automatic mode and 30 minutes in manual/off mode. Automatic mode
may be unavailable if PmSensor OUT fails. Communication failures make entities
unavailable; write failures are reported to Home Assistant.

Register definitions follow the [manufacturer's Particle+ protocol](https://thesslagreen.com/wp-content/uploads/MODBUS_USER_Particle_08.2021.01.pdf),
using function 03 and at most 16 registers per request.

### Development tests

Use a Python version supported by the installed Home Assistant release.
For current releases, create an isolated environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-test.txt
python -m pytest -q
```

Tests cover device-profile configuration, real HA coordinator/entry lifecycle and
power-sensor events, register decoding, firmware-specific alarm masks, command
validation, communication failures, and a local Modbus TCP gateway exercised by
the real pymodbus client. CI runs the minimum supported HA/pymodbus versions and
current releases. Physical-device testing is still needed.

To reproduce the minimum-version CI environment with **Python 3.13**:

```bash
python3.13 -m venv .venv-min
.venv-min/bin/python -m pip install -r requirements-test.txt \
  -c tests/constraints-ha-2025.10.txt \
  "homeassistant==2025.10.0" "pymodbus==3.11.2"
.venv-min/bin/python -m pytest -q
```

The constraint file keeps HA 2025.10's DNS dependencies compatible.
CI also runs the current HA/pymodbus releases on Python 3.14.

### Diagnostics and troubleshooting

- **Unavailable at startup:** check the gateway host/port, slave ID and RTU
  settings. Home Assistant automatically retries setup.
- **Missing optional equipment:** inspect the model sensor's
  `unsupported_registers` attribute. Only explicit Illegal Data Address responses
  are cached as unsupported; reload after changing hardware or firmware.
- **Schedule controls absent:** enable the desired entities in the device's
  entity settings. Panel changes to schedules are refreshed within five minutes.
- **Filter-replacement buttons unavailable:** select the installed AFC/timer
  arrangement in integration options; confirmation only applies to non-AFC filters.
- **COP unavailable:** use instantaneous power in W/kW, with valid temperatures,
  active CF measurements and positive power/airflow.

For release history and pending development changes, see [CHANGELOG.md](CHANGELOG.md).
