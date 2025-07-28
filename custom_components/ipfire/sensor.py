import asyncssh
from pysnmp.hlapi.asyncio import *
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from datetime import datetime
from collections import Counter

from .coordinator import IPFireCoordinator
from .const import DOMAIN

# ────────────────────────────────
# SNMP Sensor Definitions
# ────────────────────────────────

SNMP_SENSORS = [
    {"name": "IPFire Uptime", "oid": "1.3.6.1.2.1.1.3.0"},
    {"name": "IPFire CPU Load (1 min)", "oid": "1.3.6.1.4.1.2021.10.1.3.1"},
    {"name": "IPFire CPU Load (5 min)", "oid": "1.3.6.1.4.1.2021.10.1.3.2"},
    {"name": "IPFire CPU Load (15 min)", "oid": "1.3.6.1.4.1.2021.10.1.3.3"},
    {"name": "IPFire Memory Total", "oid": "1.3.6.1.4.1.2021.4.5.0"},
    {"name": "IPFire Memory Available", "oid": "1.3.6.1.4.1.2021.4.6.0"},
    {"name": "IPFire Inbound Traffic (eth0)", "oid": "1.3.6.1.2.1.2.2.1.10.2"},
    {"name": "IPFire Outbound Traffic (eth0)", "oid": "1.3.6.1.2.1.2.2.1.16.2"},
]

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

    def get_snmp_data(self):
        results = {}
        for sensor in SNMP_SENSORS:
            oid = sensor["oid"]
            try:
                iterator = getCmd(
                    SnmpEngine(),
                    CommunityData(self.snmp_community),
                    UdpTransportTarget((self.snmp_host, 161)),
                    ContextData(),
                    ObjectType(ObjectIdentity(oid))
                )
                errorIndication, errorStatus, errorIndex, varBinds = next(iterator)
                if not errorIndication and not errorStatus:
                    for varBind in varBinds:
                        results[oid] = str(varBind[1])
            except Exception as e:
                results[oid] = f"SNMP error: {e}"
        return results

    def get_ssh_data(self):
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
            result = asyncssh.run(cmd, **conn_args)
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
    api = IPFireAPI(entry.data)
    coordinator = IPFireCoordinator(hass, entry, api)
    await coordinator.async_config_entry_first_refresh()

    snmp_sensors = [
        IPFireSNMPSensor(sensor["name"], sensor["oid"], coordinator)
        for sensor in SNMP_SENSORS
    ]

    ssh_sensors = [
        IPFireSSHStatSensor("DROP_HOSTILE Count Today", "drop_hostile_total", coordinator),
        IPFireSSHStatSensor("Unique SRC IPs Today", "unique_src_ips", coordinator),
        IPFireSSHStatSensor("Top 10 DROP_HOSTILE Ports", "top_ports", coordinator),
    ]

    async_add_entities(snmp_sensors + ssh_sensors)

# ────────────────────────────────
# SNMP Sensor Class
# ────────────────────────────────

class IPFireSNMPSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, name, oid, coordinator):
        super().__init__(coordinator)
        self._attr_name = name
        self._oid = oid

    @property
    def native_value(self):
        return self.coordinator.data["snmp"].get(self._oid)

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
