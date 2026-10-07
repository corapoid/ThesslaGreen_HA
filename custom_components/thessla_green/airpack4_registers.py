"""AirPack4 user registers, MODBUS_USER_AirPack_4_10.2022.01, firmware 4.89.

Only documented addresses are requested; no reads span register-map holes.
"""

WORK_MODES = {"Automatyczny": 0, "Manualny": 1, "Chwilowy": 2}
SPECIAL_MODES = {
    0: "Brak", 1: "Okap", 2: "Kominek", 3: "Wietrzenie — przycisk",
    4: "Wietrzenie — przełącznik", 5: "Wietrzenie — higrostat",
    6: "Wietrzenie — jakość powietrza", 7: "Wietrzenie — ręczne",
    8: "Wietrzenie — harmonogram automatyczny", 9: "Wietrzenie — harmonogram manualny",
    10: "Otwarte okna", 11: "Pusty dom",
}

# key, name, address, unit, minimum, maximum, register scale
NUMBER_SETTINGS = (
    ("manual_speed", "Intensywność manualna", 4210, "%", 10, 100, 1),
    ("temporary_speed", "Intensywność chwilowa", 4211, "%", 10, 100, 1),
    ("manual_temperature", "Temperatura zadana manualna", 4212, "°C", 10, 45, 0.5),
    ("temporary_temperature", "Temperatura zadana chwilowa", 4213, "°C", 10, 45, 0.5),
    ("speed_1", "AirS — bieg 1", 4216, "%", 10, 45, 1),
    ("speed_2", "AirS — bieg 2", 4217, "%", 46, 75, 1),
    ("speed_3", "AirS — bieg 3", 4218, "%", 76, 100, 1),
    ("hood_supply", "Okap — nawiew", 4226, "%", 100, 150, 1),
    ("hood_exhaust", "Okap — wywiew", 4227, "%", 100, 150, 1),
    ("fireplace_balance", "Kominek — zwiększenie nawiewu", 4228, "%", 5, 50, 1),
    ("bathroom_intensity", "Higrostat — intensywność", 4229, "%", 100, 150, 1),
    ("airing_intensity", "Wietrzenie — intensywność", 4230, "%", 100, 150, 1),
    ("contamination_intensity", "Jakość powietrza — intensywność", 4231, "%", 100, 150, 1),
    ("empty_house_intensity", "Pusty dom — intensywność", 4232, "%", 10, 50, 1),
    ("airing_duration", "Wietrzenie — czas", 4233, "min", 1, 45, 1),
    ("airing_button_duration", "Przycisk wietrzenia — czas", 4234, "min", 1, 45, 1),
    ("airing_on_delay", "Wietrzenie — opóźnienie włączenia", 4235, "min", 0, 20, 1),
    ("airing_off_delay", "Wietrzenie — opóźnienie wyłączenia", 4236, "min", 0, 20, 1),
    ("fireplace_duration", "Kominek — czas", 4237, "min", 1, 10, 1),
    ("airing_switch_intensity", "Przełącznik wietrzenia — intensywność", 4238, "%", 100, 150, 1),
    ("window_intensity", "Otwarte okna — wywiew", 4239, "%", 10, 100, 1),
    ("gwc_min_temperature", "GWC — dolny próg temperatury", 4257, "°C", 0, 10, 0.5),
    ("gwc_max_temperature", "GWC — górny próg temperatury", 4258, "°C", 15, 40, 0.5),
    ("gwc_regeneration_duration", "GWC — czas regeneracji", 4264, "h", 4, 8, 1),
    ("gwc_regeneration_delta", "GWC — różnica temperatur regeneracji", 4266, "°C", 0, 5, 0.5),
    ("bypass_min_temperature", "Bypass — minimalna temperatura czerpni", 4321, "°C", 5, 20, 0.5),
    ("bypass_heating_temperature", "Bypass — próg freeheating", 4322, "°C", 15, 30, 0.5),
    ("bypass_cooling_temperature", "Bypass — próg freecooling", 4323, "°C", 15, 30, 0.5),
    ("bypass_balance", "Bypass — różnicowanie strumieni", 4332, "%", 10, 100, 1),
    ("bypass_intensity", "Bypass — intensywność nawiewu", 4333, "%", 10, 150, 1),
)

# Only user-resettable alarms have reset buttons. Ambiguous 0x20c6 entries
# are deliberately represented by one diagnostic flag, not invented addresses.
ALARMS = (
    (8194, "S2", "Komunikacja I2C", False),
    (8198, "S6", "Powtarzające się zabezpieczenie FPX", True),
    (8199, "S7", "Zbyt niska temperatura kalibracji", False),
    (8200, "S8", "Wymagany klucz produktu", True),
    (8201, "S9", "Zatrzymanie z AirS", False),
    (8202, "S10", "Alarm pożarowy", True),
    (8205, "S13", "Zatrzymanie z panelu", False),
    (8206, "S14", "Zabezpieczenie nagrzewnicy wodnej", True),
    (8207, "S15", "Nieskuteczne zabezpieczenie nagrzewnicy wodnej", True),
    (8208, "S16", "Zabezpieczenie termiczne FPX", False),
    (8209, "S17", "Brak wymiany filtrów — presostat", True),
    (8211, "S19", "Brak wymiany filtrów", False),
    (8212, "S20", "Brak wymiany filtra kanałowego", True),
    (8214, "S22", "Nieskuteczna ochrona przeciwzamrożeniowa", True),
    (8215, "S23", "Czujnik temperatury FPX", False),
    (8216, "S24", "Czujnik temperatury za nagrzewnicą wodną", False),
    (8217, "S25", "Czujnik temperatury zewnętrznej", False),
    (8218, "S26", "Czujniki temperatury zewnętrznej i GWC", False),
    (8220, "S28", "Sterowanie nagrzewnicą wtórną", True),
    (8221, "S29", "Zbyt wysoka temperatura przed wymiennikiem", True),
    (8222, "S30", "Awaria wentylatora nawiewu", True),
    (8223, "S31", "Awaria wentylatora wywiewu", True),
    (8224, "S32", "Brak komunikacji TG-02", True),
    (8291, "E99", "Wymagany klucz produktu", False),
    (8292, "E100", "Brak odczytu temperatury czerpni", False),
    (8293, "E101", "Brak odczytu temperatury nawiewu", False),
    (8294, "E102", "Brak odczytu temperatury wywiewu", False),
    (8295, "E103", "Brak odczytu temperatury FPX", False),
    (8296, "E104", "Brak odczytu temperatury otoczenia", False),
    (8297, "E105", "Brak odczytu temperatury kanałowej", False),
    (8298, "E106", "Brak odczytu temperatury GWC", False),
    (8300, "E108", "Brak odczytu temperatury za wymiennikiem", False),
    (8330, "E138", "Awaria CF nawiewu", False),
    (8331, "E139", "Awaria CF wywiewu", False),
    (8332, "E140", "Awaria CF filtra nawiewnego", False),
    (8333, "E141", "Awaria CF filtra wywiewnego", False),
    (8334, "F142", "Brak filtra nawiewnego", False),
    (8335, "F143", "Brak filtra wywiewnego", False),
    (8336, "E144", "Błąd utrzymania przepływu nawiewu", False),
    (8337, "E145", "Błąd utrzymania przepływu wywiewu", False),
    (8338, "F146", "Wymiana filtra nawiewnego", False),
    (8339, "F147", "Wymiana filtra wywiewnego", False),
    (8340, "E148", "Graniczne zużycie filtra nawiewnego", False),
    (8341, "E149", "Graniczne zużycie filtra wywiewnego", False),
    (8342, "E150", "Wymiana filtra nawiewnego", False),
    (8343, "E151", "Wymiana filtra wywiewnego", False),
    (8344, "E152", "Zbyt wysoka temperatura wywiewu", False),
    (8348, "E156", "Termin wymiany filtra nawiewnego", False),
    (8349, "E157", "Termin wymiany filtra wywiewnego", False),
    (8390, "E196–E198", "Regulacja instalacji / komunikacja CF", False),
    (8392, "E200", "Zabezpieczenie nagrzewnicy w centrali", False),
    (8393, "E201", "Zabezpieczenie nagrzewnicy kanałowej", False),
    (8394, "E202", "Sterowanie nagrzewnicą wtórną", True),
    (8395, "E203", "Sterowanie nagrzewnicą wtórną", True),
    (8441, "E249", "Brak komunikacji Expansion", False),
    (8443, "E251", "Wymiana filtra kanałowego", False),
)

SCHEDULE_REGISTERS = set(range(16, 128)) | {128 + day * 4 for day in range(14)}
REQUIRED_HOLDING = {256, 257, 4192, 4198, 4208, 4209, 4210, 4224, 4320, 4387, 8192, 8193}
OPTIONAL_HOLDING = (
    {13, 240, 241, 4304, 4305, 4330, 4331, 4384, 4432, 4433, 4482, 4483,
     4660, 4662, 4704, 4711, 8190, 8191, 4256, 4262, 4263, 4271}
    | {row[2] for row in NUMBER_SETTINGS}
    | {row[0] for row in ALARMS}
    | set(range(4267, 4271))
    | {4219}
    | set(range(4117, 4121)) | set(range(4354, 4358))
    | {4399} | set(range(8144, 8152))
    | set(range(1280, 1284))
) - REQUIRED_HOLDING
INPUT_REGISTERS = set(range(5)) | set(range(14, 23)) | set(range(24, 30)) | set(range(271, 278))
COIL_REGISTERS = {5, 9, 10, 11, 12, 13, 14, 15}
DISCRETE_REGISTERS = {0, 1, 3, 4, 5, 6, 7, 10, 11, 12, 13, 14, 15, 18, 19, 21}


def register_blocks(addresses, maximum=16):
    """Group adjacent documented registers into legal-sized Modbus requests."""
    blocks = []
    for address in sorted(addresses):
        if blocks and blocks[-1][0] + blocks[-1][1] == address and blocks[-1][1] < maximum:
            start, count = blocks[-1]
            blocks[-1] = (start, count + 1)
        else:
            blocks.append((address, 1))
    return blocks
