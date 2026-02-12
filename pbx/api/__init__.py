"""REST API for PBX management.

Uses Flask with Blueprints for route organization.
"""

from pbx.api.app import create_app
from pbx.api.server import PBXFlaskServer

__all__ = ["create_app", "PBXFlaskServer"]
