from homeassistant import config_entries
import voluptuous as vol
from .const import DOMAIN


class IPFireConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for IPFire."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            return self.async_create_entry(title="IPFire", data=user_input)

        data_schema = vol.Schema(
            {
                vol.Required("ssh_host"): str,
                vol.Required("ssh_port", default=222): int,
                vol.Required("ssh_user"): str,
                vol.Optional("ssh_password"): str,
                vol.Optional("ssh_key_path"): str,
                vol.Required("remote_file", default="/var/log/messages"): str,
                vol.Optional("ssh_refresh", default=3600): int,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )


