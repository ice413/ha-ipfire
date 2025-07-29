import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class IPFireCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, api):
        """Initialize the IPFire data coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        self.api = api

        self.ssh_refresh = config_entry.data.get("ssh_refresh", 3600)

        update_interval = timedelta(seconds=self.ssh_refresh)

        super().__init__(
            hass,
            _LOGGER,
            name="IPFire Data Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from IPFire via SSH."""
        try:
            ssh_data = await self.api.get_ssh_data()
            return {
                "ssh": ssh_data,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err

