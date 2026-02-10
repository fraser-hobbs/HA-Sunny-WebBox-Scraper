"""Sensor platform for SMA Sunny WebBox."""
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, SENSOR_TYPES
from .coordinator import SMAWebBoxCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SMA WebBox sensors."""
    coordinator: SMAWebBoxCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    for sensor_type, sensor_info in SENSOR_TYPES.items():
        entities.append(
            SMAWebBoxSensor(
                coordinator=coordinator,
                sensor_type=sensor_type,
                sensor_info=sensor_info,
                entry_id=entry.entry_id,
            )
        )

    async_add_entities(entities)


class SMAWebBoxSensor(CoordinatorEntity, SensorEntity):
    """Representation of an SMA WebBox sensor."""

    def __init__(
        self,
        coordinator: SMAWebBoxCoordinator,
        sensor_type: str,
        sensor_info: dict,
        entry_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_type = sensor_type
        self._attr_name = f"Solar {sensor_info['name']}"
        self._attr_unique_id = f"{entry_id}_{sensor_type}"
        self._attr_native_unit_of_measurement = sensor_info["unit"]
        self._attr_device_class = sensor_info.get("device_class")
        self._attr_state_class = sensor_info.get("state_class")
        self._attr_icon = sensor_info.get("icon")

    @property
    def native_value(self):
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get(self._sensor_type)
        return None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return self.coordinator.last_update_success
