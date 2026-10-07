"""AirPack4 filter procedures and user alarm resets."""

from .airpack4 import airpack4_entities, is_airpack4
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    if is_airpack4(entry):
        async_add_entities(airpack4_entities("button", hass.data[DOMAIN][entry.entry_id]["coordinator"], entry))
