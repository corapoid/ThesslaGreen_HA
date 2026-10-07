DOMAIN = "thessla_green"
CONF_DEVICE_TYPE = "device_type"
DEVICE_REKUPERATOR = "rekuperator"
DEVICE_PARTICLE = "particle"
DEVICE_AIRPACK4 = "airpack4_300h"
CONF_RECUPERATOR_MODEL = "recuperator_model"
CONF_FILTER_CONTROL = "filter_control"
FILTER_CONTROLS = {
    "unknown": "Nieokreślony",
    "timer": "Bez AFC",
    "afc_supply": "AFC nawiewu",
    "afc_exhaust": "AFC wywiewu",
    "afc_both": "AFC obu filtrów",
}
DEFAULT_PARTICLE_SLAVE = 30
PARTICLE_FIRMWARE_REGISTER = 8131
PARTICLE_EXTENDED_ALARMS_VERSION = 0x0304

# MODBUS_USER_Particle_08.2021.01, function 03; at most 16 registers/request.
PARTICLE_HOLDING_BLOCKS = ((16, 2), (33, 1), (36, 1), (41, 1), (48, 1),
                           (50, 5), (56, 2), (64, 2), (96, 1), (4114, 2),
                           (PARTICLE_FIRMWARE_REGISTER, 1))

CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE = "slave"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_PORT = 8899
DEFAULT_SLAVE = 10
DEFAULT_SCAN_INTERVAL = 30


def device_type(entry):
    """Allow an existing recuperator entry to opt into its model profile."""
    from collections.abc import Mapping

    configured = entry.data.get(CONF_DEVICE_TYPE, DEVICE_REKUPERATOR)
    options = getattr(entry, "options", {})
    if configured != DEVICE_PARTICLE and isinstance(options, Mapping):
        return options.get(CONF_RECUPERATOR_MODEL, configured)
    return configured
