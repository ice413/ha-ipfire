import logging
from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class IPFireCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry, api):
        """Initialize the coordinator."""
        self.hass = hass
        self.config_entry = config_entry
        self.api = api  # api should provide get_snmp_data() and get_ssh_data()
        self.snmp_refresh = config_entry.data.get("snmp_refresh", 60)
        self.ssh_refresh = config_entry.data.get("ssh_refresh", 3600)

        # Use the shortest interval for coordinator polling
        update_interval = timedelta(seconds=min(self.snmp_refresh, self.ssh_refresh))

        super().__init__(
            hass,
            _LOGGER,
            name="IPFire Data Coordinator",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        """Fetch data from IPFire via SNMP and SSH."""
        try:
            snmp_data = await self.hass.async_add_executor_job(self.api.get_snmp_data)
            ssh_data = await self.hass.async_add_executor_job(self.api.get_ssh_data)
            return {
                "snmp": snmp_data,
                "ssh": ssh_data,
            }
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")
