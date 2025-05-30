"""Sensor platform for Liberty Rider."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
import aiohttp
import async_timeout
import re
from urllib.parse import urlparse, parse_qs

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
    SensorEntityDescription,
)
from homeassistant.components.device_tracker import SourceType
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.const import (
    UnitOfLength,
    UnitOfTime,
    PERCENTAGE,
    STATE_HOME,
    STATE_NOT_HOME,
    CONF_SCAN_INTERVAL,
)
from homeassistant.helpers.translation import async_get_translations

from .const import DOMAIN, API_URL, CONF_SHARE_URL, BASE_URL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "status": SensorEntityDescription(
        key="status",
        name="entity.sensor.status.name",
        icon="mdi:map-marker-path",
    ),
    "battery": SensorEntityDescription(
        key="battery",
        name="entity.sensor.battery.name",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    "distance": SensorEntityDescription(
        key="distance",
        name="entity.sensor.distance.name",
        native_unit_of_measurement=UnitOfLength.KILOMETERS,
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "duration": SensorEntityDescription(
        key="duration",
        name="entity.sensor.duration.name",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "pause_duration": SensorEntityDescription(
        key="pause_duration",
        name="entity.sensor.pause_duration.name",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
    ),
    "start_time": SensorEntityDescription(
        key="start_time",
        name="entity.sensor.start_time.name",
        device_class=SensorDeviceClass.TIMESTAMP,
    ),
}

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Liberty Rider sensors."""
    try:
        coordinator = LibertyRiderCoordinator(hass, config_entry)
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        raise ConfigEntryNotReady(f"Error initializing Liberty Rider coordinator: {err}")

    entities = []
    
    # Ajouter tous les capteurs sauf la position
    for description in SENSOR_TYPES.values():
        entities.append(LibertyRiderSensor(coordinator, description))
    
    # Ajouter le tracker GPS
    entities.append(LibertyRiderGPSTracker(coordinator))
    
    async_add_entities(entities)

class LibertyRiderCoordinator(DataUpdateCoordinator):
    """Liberty Rider coordinator."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        scan_interval = config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name="Liberty Rider",
            update_interval=timedelta(minutes=scan_interval),
        )
        self.share_url = config_entry.data[CONF_SHARE_URL]
        self.hass = hass
        _LOGGER.debug("Processing share URL: %s", self.share_url)
        
        # Nettoyer l'URL en retirant les paramètres de tracking et le @ si présent
        if self.share_url.startswith('@'):
            self.share_url = self.share_url[1:]
        
        parsed_url = urlparse(self.share_url)
        clean_path = parsed_url.path
        
        # Extraire l'ID du trajet de l'URL (format: /fr/a/XXXXX)
        match = re.search(r'/a/([^/]+)', clean_path)
        if not match:
            _LOGGER.error("Invalid share URL format: %s", self.share_url)
            raise ValueError("Invalid share URL format")
        
        self.share_id = match.group(1)
        _LOGGER.debug("Extracted share ID: %s", self.share_id)

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    data = {
                        "operationName": "rideSharingMapByUserCurrentRideSharingToken",
                        "variables": {"token": self.share_id},
                        "extensions": {
                            "persistedQuery": {
                                "version": 1,
                                "sha256Hash": "36aac840cff92e832aa03e04b58dd2a2357d3b7459c6416c991c8862acaf3476"
                            }
                        }
                    }
                    
                    headers = {
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "x-apollo-operation-name": "rideSharingMapByUserCurrentRideSharingToken",
                        "apollo-require-preflight": "true",
                        "Origin": "https://rider.live",
                        "Referer": self.share_url
                    }
                    
                    _LOGGER.debug("Fetching ride details with share ID: %s", self.share_id)
                    
                    async with session.post(
                        API_URL,
                        json=data,
                        headers=headers
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            _LOGGER.error("API Error %d: %s", response.status, error_text)
                            raise UpdateFailed(f"Error {response.status}: {error_text}")
                        
                        data = await response.json()
                        _LOGGER.debug("Received ride details response: %s", data)
                        
                        if "errors" in data:
                            _LOGGER.error("GraphQL errors: %s", data["errors"])
                            raise UpdateFailed(f"GraphQL error: {data['errors']}")
                        
                        if not data.get("data", {}).get("ride"):
                            _LOGGER.error("No ride data found in response: %s", data)
                            raise UpdateFailed("No ride data found")
                        
                        return data["data"]["ride"]
                        
        except Exception as err:
            _LOGGER.error("Error fetching Liberty Rider data: %s", err)
            raise UpdateFailed(f"Error communicating with Liberty Rider: {err}")

class LibertyRiderSensor(SensorEntity):
    """Representation of a Liberty Rider sensor."""

    def __init__(
        self,
        coordinator: LibertyRiderCoordinator,
        description: SensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entity_description = description
        
        # Obtenir le prénom de l'utilisateur
        user_firstname = ""
        if coordinator.data and coordinator.data.get("user"):
            user = coordinator.data["user"]
            user_firstname = user.get('firstName', '')
        
        # Créer l'ID unique avec le prénom
        self._attr_unique_id = f"liberty_rider_{description.key}_{user_firstname}"
        self._attr_name = f"Liberty Rider {description.name} - {user_firstname}"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Return device info."""
        if not self.coordinator.data or not self.coordinator.data.get("user"):
            return None
            
        user = self.coordinator.data["user"]
        return {
            "identifiers": {(DOMAIN, self.coordinator.share_id)},
            "name": f"Liberty Rider - {user.get('firstName', '')}",
            "manufacturer": "Liberty Rider",
            "model": "Liberty Rider",
        }

    @property
    def state(self):
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        try:
            data = self.coordinator.data
            
            if self.entity_description.key == "status":
                state = data.get("state")
                if state is None:
                    return None
                return f"entity.sensor.status.state.{state.lower()}"
                
            elif self.entity_description.key == "battery":
                battery_level = data.get("currentBatteryLevel")
                if battery_level is None:
                    return None
                return float(battery_level)
                
            elif self.entity_description.key == "distance":
                distance = data.get("distance")
                if distance is None:
                    return None
                return float(distance) / 1000  # Convertir en kilomètres
                
            elif self.entity_description.key == "duration":
                duration = data.get("duration")
                if duration is None:
                    return None
                return int(duration / 60)  # Convertir en minutes
                
            elif self.entity_description.key == "pause_duration":
                pause_duration = data.get("pauseDuration")
                if pause_duration is None:
                    return None
                return int(pause_duration / 60)  # Convertir en minutes
                
            elif self.entity_description.key == "start_time":
                start_time = data.get("startTime")
                if start_time is None:
                    return None
                return datetime.fromisoformat(start_time.replace("Z", "+00:00"))
                
        except Exception as err:
            _LOGGER.error("Error getting sensor state: %s", err)
            return None

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()

class LibertyRiderGPSTracker(TrackerEntity):
    """Representation of a Liberty Rider GPS tracker."""

    def __init__(self, coordinator: LibertyRiderCoordinator) -> None:
        """Initialize the GPS tracker."""
        self.coordinator = coordinator
        
        # Obtenir le prénom de l'utilisateur
        user_firstname = ""
        if coordinator.data and coordinator.data.get("user"):
            user = coordinator.data["user"]
            user_firstname = user.get('firstName', '')
        
        # Créer l'ID unique avec le prénom
        self._attr_unique_id = f"liberty_rider_{user_firstname}_gps"
        self._attr_name = f"Liberty Rider GPS - {user_firstname}"
        self._attr_icon = "mdi:map-marker"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    @property
    def device_info(self):
        """Return device info."""
        if not self.coordinator.data or not self.coordinator.data.get("user"):
            return None
            
        user = self.coordinator.data["user"]
        return {
            "identifiers": {(DOMAIN, self.coordinator.share_id)},
            "name": f"Liberty Rider - {user.get('firstName', '')}",
            "manufacturer": "Liberty Rider",
            "model": "Liberty Rider",
        }

    @property
    def source_type(self) -> SourceType:
        """Return the source type of the device tracker."""
        return SourceType.GPS

    @property
    def state(self) -> str:
        """Return the state of the device tracker."""
        if not self.coordinator.data:
            return STATE_NOT_HOME
            
        state = self.coordinator.data.get("state")
        if state:
            return f"entity.sensor.status.state.{state.lower()}"
        return STATE_NOT_HOME

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if not self.coordinator.data:
            return None
            
        try:
            data = self.coordinator.data
            state = data.get("state")
            
            # Si le trajet est actif, essayer d'obtenir la position actuelle
            if state == "RIDE_ACTIVE":
                # Vérifier s'il y a une position actuelle dans les données
                current_location = data.get("currentLocation")
                if current_location and current_location.get("latitude"):
                    return float(current_location["latitude"])
            
            # Sinon, obtenir la dernière position connue depuis les pauses
            if state in ["RIDE_PAUSED", "RIDE_STOPPED"]:
                pauses = data.get("pauses", [])
                if pauses:
                    last_pause = pauses[-1]
                    location = last_pause.get("lastLocation", {})
                    if location and location.get("latitude"):
                        return float(location["latitude"])
            
            return None
            
        except (KeyError, TypeError, AttributeError, ValueError) as err:
            _LOGGER.warning("Error getting latitude: %s", err)
            return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if not self.coordinator.data:
            return None
            
        try:
            data = self.coordinator.data
            state = data.get("state")
            
            # Si le trajet est actif, essayer d'obtenir la position actuelle
            if state == "RIDE_ACTIVE":
                # Vérifier s'il y a une position actuelle dans les données
                current_location = data.get("currentLocation")
                if current_location and current_location.get("longitude"):
                    return float(current_location["longitude"])
            
            # Sinon, obtenir la dernière position connue depuis les pauses
            if state in ["RIDE_PAUSED", "RIDE_STOPPED"]:
                pauses = data.get("pauses", [])
                if pauses:
                    last_pause = pauses[-1]
                    location = last_pause.get("lastLocation", {})
                    if location and location.get("longitude"):
                        return float(location["longitude"])
            
            return None
            
        except (KeyError, TypeError, AttributeError, ValueError) as err:
            _LOGGER.warning("Error getting longitude: %s", err)
            return None

    @property
    def location_accuracy(self) -> int:
        """Return the location accuracy of the device."""
        # Retourner une précision par défaut en mètres
        return 10

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes."""
        if not self.coordinator.data:
            return {}
            
        try:
            data = self.coordinator.data
            attributes = {}
            
            # Ajouter des informations sur le trajet
            if data.get("state"):
                attributes["ride_status"] = f"entity.sensor.status.state.{data['state'].lower()}"
            
            if data.get("distance"):
                attributes["distance_km"] = round(data["distance"] / 1000, 2)
            
            if data.get("duration"):
                attributes["duration_minutes"] = round(data["duration"] / 60, 1)
            
            if data.get("currentBatteryLevel"):
                attributes["battery_level"] = round(data["currentBatteryLevel"] * 100, 1)
            
            return attributes
            
        except Exception as err:
            _LOGGER.warning("Error getting extra attributes: %s", err)
            return {}

    async def async_update(self) -> None:
        """Update the entity."""
        await self.coordinator.async_request_refresh()