import asyncio
import asyncssh
from datetime import datetime
from collections import Counter

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import IPFireCoordinator
from .const import DOMAIN


# ────────────────────────────────
# API Class for Coordinator
# ────────────────────────────────

class IPFireAPI:
    def __init__(self, config):
        self.ssh_host = config["ssh_host"]
        self.ssh_port = config["ssh_port"]
        self.ssh_user = config["ssh_user"]
        self.ssh_password = config.get("ssh_password")
        self.ssh_key_path = config.get("ssh_key_path")
        self.remote_file = config["remote_file"]
        self.snmp_host = config["snmp_host"]
        self.snmp_community = config["snmp_community"]

    async def get_ssh_data(self):
        today = datetime.now().strftime("%b %e")
        drop_hostile_total = 0
        unique_ips = set()
        port_counter = Counter()

        cmd = f"cat {self.remote_file}"
        conn_args = {
            "host": self.ssh_host,
            "port": self.ssh_port,
            "username": self.ssh_user,
        }
        if self.ssh_key_path:
            conn_args["client_keys"] = [self.ssh_key_path]
        else:
            conn_args["password"] = self.ssh_password

        try:
            async with asyncssh.connect(**conn_args) as conn:
                result = await conn.run(cmd, check=True)
                lines = result.stdout.splitlines()
        except Exception as e:
            return {
                "drop_hostile_total": f"SSH error: {e}",
                "unique_src_ips": None,
                "top_ports": None,
                "top_ports_raw": {},
            }

        for line in lines:
            if today in line and "DROP_HOSTILE" in line:
                drop_hostile_total += 1
                parts = line.split()
                src_ip = None
                dpt = None
                for part in parts:
                    if part.startswith("SRC="):
                        src_ip = part.split("=")[1]
                        unique_ips.add(src_ip)
                    if part.startswith("DPT="):
                        dpt = part.split("=")[1]
                if dpt:
                    port_counter[dpt] += 1

        top_ports_raw = dict(port_counter.most_common(10))
        top_port = next(iter(top_ports_raw), None)

        return {
            "drop_hostile_total": drop_hostile_total,
            "unique_src_ips": len(unique_ips),
            "top_ports": top_port,
            "top_ports_raw": top_ports_raw,
        }

# ────────────────────────────────
# Setup Entry
# ────────────────────────────────

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    ssh_sensors = [
        IPFireSSHStatSensor("DROP_HOSTILE Count Today", "drop_hostile_total", coordinator),
        IPFireSSHStatSensor("Unique SRC IPs Today", "unique_src_ips", coordinator),
        IPFireSSHStatSensor("Top 10 DROP_HOSTILE Ports", "top_ports", coordinator),
    ]

    async_add_entities(ssh_sensors)

# ────────────────────────────────
# SSH Sensor Class
# ────────────────────────────────

class IPFireSSHStatSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, name, key, coordinator):
        super().__init__(coordinator)
        self._attr_name = name
        self._key = key

    @property
    def native_value(self):
        return self.coordinator.data["ssh"].get(self._key)

    @property
    def extra_state_attributes(self):
        if self._key == "top_ports":
            return {"top_ports": self.coordinator.data["ssh"].get("top_ports_raw", {})}
        return {}
