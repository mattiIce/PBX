"""
SIP Trunk Support
Allows external calls through SIP providers
"""
from enum import Enum

from pbx.utils.e911_protection import E911Protection
from pbx.utils.logger import get_logger


class TrunkStatus(Enum):
    """SIP trunk status"""
    REGISTERED = "registered"
    UNREGISTERED = "unregistered"
    FAILED = "failed"
    DISABLED = "disabled"


class SIPTrunk:
    """Represents a SIP trunk connection"""

    def __init__(self, trunk_id, name, host, username, password,
                 port=5060, codec_preferences=None):
        """
        Initialize SIP trunk

        Args:
            trunk_id: Trunk identifier
            name: Trunk name
            host: SIP provider host
            username: SIP username
            password: SIP password
            port: SIP port (default 5060)
            codec_preferences: List of preferred codecs
        """
        self.trunk_id = trunk_id
        self.name = name
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.codec_preferences = codec_preferences or ['G.711', 'G.729']
        self.status = TrunkStatus.UNREGISTERED
        self.channels_available = 0
        self.channels_in_use = 0
        self.logger = get_logger()

    def register(self):
        """
        Register trunk with provider

        Returns:
            True if registration successful
        """
        self.logger.info(f"Registering SIP trunk {self.name} with {self.host}")

        # In a real implementation:
        # 1. Send SIP REGISTER to provider
        # 2. Handle authentication challenge
        # 3. Maintain registration with periodic re-REGISTER

        self.status = TrunkStatus.REGISTERED
        return True

    def unregister(self):
        """Unregister trunk"""
        self.logger.info(f"Unregistering SIP trunk {self.name}")
        self.status = TrunkStatus.UNREGISTERED

    def can_make_call(self):
        """Check if trunk can make call"""
        return (self.status == TrunkStatus.REGISTERED and
                self.channels_in_use < self.channels_available)

    def allocate_channel(self):
        """Allocate channel for outbound call"""
        if self.can_make_call():
            self.channels_in_use += 1
            return True
        return False

    def release_channel(self):
        """Release channel"""
        if self.channels_in_use > 0:
            self.channels_in_use -= 1

    def to_dict(self):
        """Convert to dictionary"""
        return {
            'trunk_id': self.trunk_id,
            'name': self.name,
            'host': self.host,
            'port': self.port,
            'username': self.username,
            'status': self.status.value,
            'channels_available': self.channels_available,
            'channels_in_use': self.channels_in_use,
            'codec_preferences': self.codec_preferences
        }


class OutboundRule:
    """Routing rule for outbound calls"""

    def __init__(self, rule_id, pattern, trunk_id, prepend="", strip=0):
        """
        Initialize outbound rule

        Args:
            rule_id: Rule identifier
            pattern: Dial pattern (regex)
            trunk_id: Trunk to use
            prepend: Digits to prepend
            strip: Number of digits to strip from beginning
        """
        self.rule_id = rule_id
        self.pattern = pattern
        self.trunk_id = trunk_id
        self.prepend = prepend
        self.strip = strip

    def matches(self, number):
        """
        Check if number matches pattern

        Args:
            number: Dialed number

        Returns:
            True if matches
        """
        import re
        return bool(re.match(self.pattern, number))

    def transform_number(self, number):
        """
        Transform number according to rule

        Args:
            number: Original number

        Returns:
            Transformed number
        """
        # Strip digits
        if self.strip > 0:
            number = number[self.strip:]

        # Prepend digits
        if self.prepend:
            number = self.prepend + number

        return number


class SIPTrunkSystem:
    """Manages SIP trunks for external calls"""

    def __init__(self, config=None):
        """Initialize SIP trunk system

        Args:
            config: Configuration object (optional)
        """
        self.trunks = {}
        self.outbound_rules = []
        self.logger = get_logger()
        self.e911_protection = E911Protection(config)

    def add_trunk(self, trunk):
        """
        Add SIP trunk

        Args:
            trunk: SIPTrunk object
        """
        self.trunks[trunk.trunk_id] = trunk
        self.logger.info(f"Added SIP trunk: {trunk.name}")

    def remove_trunk(self, trunk_id):
        """Remove SIP trunk"""
        if trunk_id in self.trunks:
            trunk = self.trunks[trunk_id]
            trunk.unregister()
            del self.trunks[trunk_id]
            self.logger.info(f"Removed SIP trunk: {trunk_id}")

    def get_trunk(self, trunk_id):
        """Get trunk by ID"""
        return self.trunks.get(trunk_id)

    def register_all(self):
        """Register all trunks"""
        for trunk in self.trunks.values():
            trunk.register()

    def add_outbound_rule(self, rule):
        """
        Add outbound routing rule

        Args:
            rule: OutboundRule object
        """
        self.outbound_rules.append(rule)
        self.logger.info(
            f"Added outbound rule: {rule.pattern} -> trunk {rule.trunk_id}")

    def route_outbound(self, number):
        """
        Route outbound call

        Args:
            number: Dialed number

        Returns:
            Tuple of (trunk, transformed_number) or (None, None)
        """
        # Block E911 calls in test mode
        if self.e911_protection.block_if_e911(
                number, context="route_outbound"):
            self.logger.error(
                f"E911 call to {number} blocked by protection system")
            return (None, None)

        for rule in self.outbound_rules:
            if rule.matches(number):
                trunk = self.get_trunk(rule.trunk_id)

                if trunk and trunk.can_make_call():
                    transformed = rule.transform_number(number)
                    self.logger.info(
                        f"Routing {number} -> {transformed} via trunk {trunk.name}")
                    return (trunk, transformed)

        self.logger.warning(f"No route found for outbound number {number}")
        return (None, None)

    def get_trunk_status(self):
        """Get status of all trunks"""
        return [trunk.to_dict() for trunk in self.trunks.values()]

    def make_outbound_call(self, from_extension, to_number):
        """
        Initiate outbound call

        Args:
            from_extension: Calling extension
            to_number: External number to call

        Returns:
            True if call initiated
        """
        # Block E911 calls in test mode
        if self.e911_protection.block_if_e911(
                to_number, context="make_outbound_call"):
            self.logger.error(
                f"E911 call from {from_extension} to {to_number} blocked by protection system")
            return False

        trunk, transformed_number = self.route_outbound(to_number)

        if not trunk:
            return False

        if trunk.allocate_channel():
            self.logger.info(
                f"Making outbound call from {from_extension} to {transformed_number}")

            # In a real implementation:
            # 1. Build SIP INVITE to trunk
            # 2. Include authentication
            # 3. Bridge with internal extension
            # 4. Handle call progress

            return True

        return False
