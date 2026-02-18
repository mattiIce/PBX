"""
Paging System Feature
Provides support for overhead paging via digital-to-analog converters
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pbx.utils.logger import get_logger


class PagingSystem:
    """
    Paging system for overhead announcements

    Provides full paging functionality including:
    - Digital-to-analog converter integration via SIP gateways
    - Paging zones management with per-zone DAC device mapping
    - Paging call routing through the PBX core's paging handler
    - Multi-zone and all-call paging support
    - SIP INVITE-based audio streaming to DAC devices
    - Emergency override capabilities
    """

    def __init__(self, config: dict, database: Any | None = None) -> None:
        """
        Initialize paging system

        Args:
            config: Configuration dictionary
            database: Optional DatabaseBackend instance
        """
        self.logger = get_logger()
        self.config = config
        self.database = database
        self.enabled = config.get("features.paging.enabled", False)

        # Paging configuration
        self.paging_prefix = config.get("features.paging.prefix", "7")  # Dial 7xx for paging
        self.zones = config.get("features.paging.zones", [])
        self.all_call_extension = config.get("features.paging.all_call_extension", "700")

        # Digital-to-analog converter settings
        self.dac_type = config.get("features.paging.dac_type", "sip_gateway")  # or 'analog_gateway'
        self.dac_devices = config.get("features.paging.dac_devices", [])

        # Active paging sessions
        self.active_pages = {}  # {page_id: page_info}

        # Maximum page duration in seconds (0 = unlimited)
        self.max_page_duration = config.get("features.paging.max_duration", 120)

        # Reference to PBX core (set by FeatureInitializer after construction)
        self.pbx_core = None

        if self.enabled:
            self.logger.info("Paging system enabled")
            self.logger.info(f"Paging prefix: {self.paging_prefix}")
            self.logger.info(f"All-call extension: {self.all_call_extension}")
            self.logger.info(f"Configured zones: {len(self.zones)}")
            self.logger.info(f"DAC devices: {len(self.dac_devices)}")
            if not self.dac_devices:
                self.logger.warning(
                    "No DAC devices configured. Paging calls will be answered "
                    "but audio will not be routed to speakers until a DAC device "
                    "is configured in features.paging.dac_devices."
                )
        else:
            self.logger.info("Paging system disabled")

    def is_paging_extension(self, extension: str) -> bool:
        """
        Check if an extension is a paging extension

        Args:
            extension: Extension number

        Returns:
            bool: True if this is a paging extension
        """
        if not self.enabled:
            return False

        # Check if starts with paging prefix
        if extension.startswith(self.paging_prefix):
            return True

        # Check if it's the all-call extension
        return extension == self.all_call_extension

    def get_zone_for_extension(self, extension: str) -> dict | None:
        """
        Get the paging zone for a given extension

        Args:
            extension: Extension number

        Returns:
            dict: Zone information or None
        """
        if not self.enabled:
            return None

        for zone in self.zones:
            if zone.get("extension") == extension:
                return zone

        return None

    def initiate_page(self, from_extension: str, to_extension: str) -> str | None:
        """
        Initiate a paging call

        Args:
            from_extension: Calling extension
            to_extension: Paging extension (zone)

        Returns:
            str: Page ID if successful, None otherwise
        """
        if not self.enabled:
            self.logger.warning("Paging system is disabled")
            return None

        if not self.is_paging_extension(to_extension):
            self.logger.warning(f"Extension {to_extension} is not a paging extension")
            return None

        # Generate page ID with UUID to ensure uniqueness
        page_id = f"page-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{from_extension}-{uuid.uuid4().hex[:8]}"

        # Determine zone(s)
        if to_extension == self.all_call_extension:
            zones = self.zones  # All zones
            zone_names = "All Zones"
        else:
            zone = self.get_zone_for_extension(to_extension)
            if zone:
                zones = [zone]
                zone_names = zone.get("name", to_extension)
            else:
                self.logger.warning(f"No zone configured for extension {to_extension}")
                return None

        # Store page information
        page_info = {
            "page_id": page_id,
            "from_extension": from_extension,
            "to_extension": to_extension,
            "zones": zones,
            "zone_names": zone_names,
            "started_at": datetime.now(UTC),
            "status": "active",
        }

        self.active_pages[page_id] = page_info

        self.logger.info(f"Paging initiated: {from_extension} -> {zone_names} (Page ID: {page_id})")

        # Resolve DAC devices for the target zones so the PBX core's paging handler
        # can route RTP audio to the correct gateway.  Attach the resolved device info
        # to the page_info so callers (PagingHandler) can look it up via get_page_info().
        resolved_devices = []
        for zone in zones:
            dac_device_id = zone.get("dac_device")
            if dac_device_id:
                for device in self.dac_devices:
                    if device.get("device_id") == dac_device_id:
                        resolved_devices.append(device)
                        break

        page_info["resolved_dac_devices"] = resolved_devices

        if not resolved_devices:
            self.logger.warning(
                f"No DAC devices resolved for page {page_id}. Audio will not "
                f"be routed to speakers. The SIP call is still answered so the "
                f"caller hears confirmation, but no physical paging output occurs."
            )

        # Schedule automatic page timeout if max_page_duration is configured
        if self.max_page_duration > 0:
            import threading

            def _auto_end_page() -> None:
                if page_id in self.active_pages:
                    self.logger.warning(
                        f"Page {page_id} exceeded max duration "
                        f"({self.max_page_duration}s), ending automatically"
                    )
                    self.end_page(page_id)
                    # Also end the associated call via PBX core if available
                    if self.pbx_core:
                        # Find and end the call associated with this page
                        for call in self.pbx_core.call_manager.get_active_calls():
                            if hasattr(call, "page_id") and call.page_id == page_id:
                                self.pbx_core.end_call(call.call_id)
                                break

            timer = threading.Timer(self.max_page_duration, _auto_end_page)
            timer.daemon = True
            timer.start()
            page_info["timeout_timer"] = timer

        return page_id

    def end_page(self, page_id: str) -> bool:
        """
        End an active page

        Args:
            page_id: Page identifier

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        if page_id not in self.active_pages:
            self.logger.warning(f"Page {page_id} not found")
            return False

        page_info = self.active_pages[page_id]
        page_info["status"] = "ended"
        page_info["ended_at"] = datetime.now(UTC)

        # Cancel the auto-timeout timer if one was set
        timeout_timer = page_info.get("timeout_timer")
        if timeout_timer is not None:
            timeout_timer.cancel()

        # Calculate page duration for logging
        started_at = page_info.get("started_at")
        if started_at:
            duration = (datetime.now(UTC) - started_at).total_seconds()
            self.logger.info(
                f"Page ended: {page_id} ({page_info['zone_names']}) duration={duration:.1f}s"
            )
        else:
            self.logger.info(f"Page ended: {page_id} ({page_info['zone_names']})")

        # Remove from active pages
        del self.active_pages[page_id]

        return True

    def get_active_pages(self) -> list[dict]:
        """
        Get all active paging sessions

        Returns:
            list: list of active page dictionaries
        """
        if not self.enabled:
            return []

        return list(self.active_pages.values())

    def get_page_info(self, page_id: str) -> dict | None:
        """
        Get information about a specific page

        Args:
            page_id: Page identifier

        Returns:
            dict: Page information or None
        """
        if not self.enabled:
            return None

        return self.active_pages.get(page_id)

    def get_zones(self) -> list[dict]:
        """
        Get all configured paging zones

        Returns:
            list: list of zone dictionaries
        """
        if not self.enabled:
            return []

        return self.zones

    def add_zone(
        self,
        extension: str,
        name: str,
        description: str | None = None,
        dac_device: str | None = None,
    ) -> bool:
        """
        Add a paging zone (runtime configuration)

        Args:
            extension: Extension number for this zone
            name: Zone name
            description: Zone description (optional)
            dac_device: DAC device identifier (optional)

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        zone = {
            "extension": extension,
            "name": name,
            "description": description,
            "dac_device": dac_device,
            "created_at": datetime.now(UTC),
        }

        # Check if zone already exists
        for existing_zone in self.zones:
            if existing_zone.get("extension") == extension:
                self.logger.warning(f"Zone {extension} already exists")
                return False

        self.zones.append(zone)
        self.logger.info(f"Added paging zone: {extension} - {name}")

        # Note: This only adds to runtime configuration
        # To persist, this should be saved to config.yml or database

        return True

    def remove_zone(self, extension: str) -> bool:
        """
        Remove a paging zone

        Args:
            extension: Extension number

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        for i, zone in enumerate(self.zones):
            if zone.get("extension") == extension:
                removed_zone = self.zones.pop(i)
                self.logger.info(f"Removed paging zone: {extension} - {removed_zone.get('name')}")
                return True

        self.logger.warning(f"Zone {extension} not found")
        return False

    def configure_dac_device(
        self,
        device_id: str,
        device_type: str,
        sip_uri: str | None = None,
        ip_address: str | None = None,
        port: int = 5060,
    ) -> bool:
        """
        Configure a digital-to-analog converter device

        Args:
            device_id: Device identifier
            device_type: type of device (e.g., 'cisco_vg', 'grandstream_ht')
            sip_uri: SIP URI for the device
            ip_address: IP address of the device
            port: SIP port (default 5060)

        Returns:
            bool: True if successful
        """
        if not self.enabled:
            return False

        device = {
            "device_id": device_id,
            "device_type": device_type,
            "sip_uri": sip_uri,
            "ip_address": ip_address,
            "port": port,
            "configured_at": datetime.now(UTC),
        }

        # Check if device already exists
        for existing_device in self.dac_devices:
            if existing_device.get("device_id") == device_id:
                self.logger.warning(f"DAC device {device_id} already exists")
                return False

        self.dac_devices.append(device)
        self.logger.info(f"Configured DAC device: {device_id} ({device_type})")

        return True

    def get_dac_devices(self) -> list[dict]:
        """
        Get all configured DAC devices

        Returns:
            list: list of DAC device dictionaries
        """
        if not self.enabled:
            return []

        return self.dac_devices
