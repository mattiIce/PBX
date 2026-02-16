"""
Paging System Feature
Provides support for overhead paging via digital-to-analog converters
"""

import uuid
from datetime import UTC, datetime

from pbx.utils.logger import get_logger
from typing import Any


class PagingSystem:
    """
    Paging system for overhead announcements

    This is a stub implementation that provides the framework for:
    - Digital-to-analog converter integration
    - Paging zones management
    - Paging call routing
    - Multi-zone paging support

    Future implementation will include:
    - Integration with SIP-to-analog gateways (e.g., Cisco VG series, Grandstream HT series)
    - Audio streaming to analog outputs
    - Zone-based paging with individual control
    - All-call paging support
    - Emergency override capabilities
    """

    def __init__(self, config: dict, database: Any | None =None) -> None:
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

        if self.enabled:
            self.logger.info("Paging system enabled (STUB IMPLEMENTATION)")
            self.logger.info(f"Paging prefix: {self.paging_prefix}")
            self.logger.info(f"All-call extension: {self.all_call_extension}")
            self.logger.info(f"Configured zones: {len(self.zones)}")
            self.logger.warning(
                "NOTE: This is a stub implementation. Full paging requires hardware integration."
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

        # Note: Actual audio routing is handled by PBX core's _handle_paging() and _paging_session() methods
        # The core PBX will:
        # 1. Answer the SIP call from the paging initiator
        # 2. Allocate RTP ports for audio relay
        # 3. Route RTP audio stream to DAC device (when hardware is available)
        # 4. Handle zone selection on multi-zone gateways
        # 5. Manage page duration and automatic timeout
        # 6. Call end_page() when the caller hangs up

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

        self.logger.info(f"Page ended: {page_id} ({page_info['zone_names']})")

        # Remove from active pages
        del self.active_pages[page_id]

        # Note: Actual page termination is handled by PBX core's _paging_session() method
        # The core PBX will close the SIP session and stop audio streaming when:
        # 1. The caller hangs up (BYE message received)
        # 2. A timeout occurs (if configured)
        # 3. Manual termination is requested via API

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


# Implementation notes for future development:
#
# To implement full paging functionality, the following steps are needed:
#
# 1. Hardware Setup:
#    - Install a SIP-to-analog gateway device (e.g., Cisco VG202, VG204, VG224)
#    - Or use an analog telephone adapter (ATA) like Grandstream HT801/HT802
#    - Connect analog output to overhead paging amplifier
#    - Configure the gateway with a SIP account on the PBX
#
# 2. Software Integration:
#    - Extend this stub to handle SIP INVITE to the gateway device
#    - Route RTP audio stream from calling extension to gateway
#    - Handle DTMF tones for zone selection (if multi-zone)
#    - Implement auto-answer on gateway side
#    - Add timeout handling (e.g., max 2 minutes per page)
#
# 3. Configuration:
#    - Add gateway device to config.yml under features.paging.dac_devices
#    - Define zones with their corresponding extensions
#    - Map zones to specific analog outputs on multi-port gateways
#    - Configure audio levels and quality settings
#
# 4. Advanced Features:
#    - Priority paging (emergency override)
#    - Scheduled paging (e.g., bell schedules)
#    - Background music integration
#    - Recording of pages for compliance
#    - Integration with emergency notification systems
#
# Example configuration in config.yml:
#
# features:
#   paging:
#     enabled: true
#     prefix: "7"
#     all_call_extension: "700"
#     dac_type: "sip_gateway"
#     dac_devices:
#       - device_id: "paging-gateway-1"
#         device_type: "cisco_vg224"
#         sip_uri: "sip:paging@192.168.1.100:5060"
#         ip_address: "192.168.1.100"
#         port: 5060
#     zones:
#       - extension: "701"
#         name: "Zone 1 - Office"
#         description: "Main office area"
#         dac_device: "paging-gateway-1"
#         analog_port: 1
#       - extension: "702"
#         name: "Zone 2 - Warehouse"
#         description: "Warehouse and loading dock"
#         dac_device: "paging-gateway-1"
#         analog_port: 2
#       - extension: "703"
#         name: "Zone 3 - Outside"
#         description: "Exterior speakers"
#         dac_device: "paging-gateway-1"
#         analog_port: 3
#
