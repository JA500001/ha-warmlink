from .const import DOMAIN
from .coordinator import WarmlinkCoordinator
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er
import voluptuous as vol
import logging

LOGGER = logging.getLogger(__name__)

# Configured via config entries (UI) only, not via YAML.
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

PLATFORMS = ["sensor", "button", "switch", "select", "water_heater", "climate"]

SERVICE_SET_VALUE = "set_value"
ATTR_ENTITY_ID = "entity_id"
ATTR_CODE = "code"
ATTR_VALUE = "value"

SET_VALUE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
        vol.Required(ATTR_CODE): cv.string,
        vol.Required(ATTR_VALUE): vol.Coerce(str),
    }
)


async def async_setup(hass, config):
    """Set up the WarmLink component."""
    hass.data.setdefault(DOMAIN, {})

    async def async_set_value(call):
        """Write an arbitrary supported WarmLink protocol code."""
        entity_id = call.data[ATTR_ENTITY_ID]
        code = call.data[ATTR_CODE]
        value = call.data[ATTR_VALUE]

        registry = er.async_get(hass)
        entity_entry = registry.async_get(entity_id)
        if entity_entry is None:
            raise ValueError(f"WarmLink entity not found: {entity_id}")

        config_entry_id = entity_entry.config_entry_id
        if not config_entry_id:
            raise ValueError(f"Entity is not associated with a WarmLink config entry: {entity_id}")

        coord = hass.data.get(DOMAIN, {}).get(config_entry_id)
        if coord is None:
            raise ValueError(f"WarmLink config entry is not loaded: {config_entry_id}")

        if code not in coord.codes:
            raise ValueError(
                f"Unsupported WarmLink protocol code for this device: {code}"
            )

        device_code = coord._device_code
        if not device_code:
            raise ValueError("WarmLink device code is not available")

        result = await coord.api.set_value(device_code, code, value)
        LOGGER.info(
            "WarmLink service set_value: %s=%s on device %s",
            code,
            value,
            device_code,
        )

        # Refresh promptly so the corresponding sensor reflects the new value.
        await coord.async_request_refresh()

        return result

    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_VALUE,
        async_set_value,
        schema=SET_VALUE_SCHEMA,
    )

    return True


async def async_setup_entry(hass, entry):
    """Set up WarmLink from a config entry."""
    coord = WarmlinkCoordinator(hass, entry)

    # Perform first refresh to get initial data
    await coord.async_config_entry_first_refresh()

    # Store coordinator
    hass.data[DOMAIN][entry.entry_id] = coord

    # Forward setup to platforms (this will create sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Add update listener for config changes
    entry.async_on_unload(entry.add_update_listener(update_listener))

    LOGGER.info(f"WarmLink: Integration setup complete. Update interval: {coord.update_interval}")

    return True


async def update_listener(hass, entry):
    """Handle config entry update."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass, entry):
    """Unload a WarmLink config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        # Release the shared API client from the pool when no other loaded entry
        # uses the same account. Otherwise a reconfigure that changes the password
        # (same username) would reuse the pooled client — and its stale token —
        # until the next full HA restart.
        username = entry.data.get("username")
        pool = hass.data.get(DOMAIN, {}).get("_api_pool", {})
        if username in pool:
            others = [
                e for e in hass.config_entries.async_entries(DOMAIN)
                if e.entry_id != entry.entry_id and e.data.get("username") == username
            ]
            if not others:
                pool.pop(username, None)
                LOGGER.debug("WarmLink: Released pooled API client for account %s", username)
    return unload_ok
