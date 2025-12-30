"""
Warden Voip System Integrations Package

Provides both proprietary and free/open-source integrations.
All integrations are optional and can be enabled/disabled in config.yml.

Free & Open Source Integrations (Recommended):
- Jitsi Meet: Video conferencing (alternative to Zoom)
- EspoCRM: Customer relationship management (alternative to Salesforce/HubSpot)
- Matrix: Team messaging (alternative to Slack/Teams)
- OpenLDAP: Directory services (compatible with Active Directory integration)
- Vosk: Speech recognition (already integrated, see voicemail_transcription.py)

Proprietary Integrations (Optional, require licenses):
- Zoom: Video conferencing and Zoom Phone
- Microsoft Teams: Collaboration and calling
- Microsoft Outlook: Calendar and contacts
- Active Directory: Enterprise directory (also works with OpenLDAP)
- Lansweeper: IT asset management
"""

# Note: Integration classes are not imported here to avoid circular imports
# and to allow for optional dependencies. Import them directly from their modules.
__all__ = []
