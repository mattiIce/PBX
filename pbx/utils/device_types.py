"""
Device type Detection Utilities

This module provides shared constants and utilities for detecting device types
(ATA vs Phone) based on vendor and model information. Used by both the database
layer and phone provisioning layer to ensure consistent device classification.
"""

# Known ATA models by vendor
ATA_MODELS = {
    "cisco": ["ata191", "ata192", "spa112", "spa122"],
    "grandstream": ["ht801", "ht802", "ht812", "ht814", "ht818"],
    "obihai": ["obi200", "obi202", "obi300", "obi302", "obi504", "obi508"],
}

# Keywords for detecting ATAs when exact model match fails
# Only include generic patterns not already covered by exact model matching
ATA_KEYWORDS = ["ata", "obi"]


def detect_device_type(vendor: str, model: str) -> str:
    """
    Detect device type based on vendor and model

    Args:
        vendor: Device vendor
        model: Device model

    Returns:
        str: 'ata' or 'phone'
    """
    # Convert to lowercase for comparison
    vendor_lower = vendor.lower()
    model_lower = model.lower()

    # Check if model is an ATA via exact match
    if vendor_lower in ATA_MODELS:
        if model_lower in ATA_MODELS[vendor_lower]:
            return "ata"

    # Check for common ATA keywords in model name (for unknown/new models)
    for keyword in ATA_KEYWORDS:
        if keyword in model_lower:
            return "ata"

    # Default to phone
    return "phone"
