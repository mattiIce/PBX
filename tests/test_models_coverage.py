"""
Comprehensive tests for PBX ORM models:
  - Base (DeclarativeBase)
  - TimestampMixin
  - Extension
  - CallRecord
  - Voicemail
  - RegisteredPhone
"""

from collections.abc import Generator
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, create_engine, inspect
from sqlalchemy.orm import Mapped, Session

from pbx.models.base import Base, TimestampMixin
from pbx.models.call_record import CallRecord
from pbx.models.extension import Extension
from pbx.models.registered_phone import RegisteredPhone
from pbx.models.voicemail import Voicemail


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide an in-memory SQLite session for model testing."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Base & TimestampMixin
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBase:
    """Tests for the SQLAlchemy declarative Base."""

    def test_base_is_declarative_base(self) -> None:
        """Base should be a valid SQLAlchemy DeclarativeBase subclass."""
        assert hasattr(Base, "metadata")
        assert hasattr(Base, "registry")

    def test_base_metadata_contains_tables(self) -> None:
        """Metadata should be aware of registered model tables."""
        table_names = Base.metadata.tables.keys()
        assert "extensions" in table_names
        assert "call_records" in table_names
        assert "voicemails" in table_names
        assert "registered_phones" in table_names


@pytest.mark.unit
class TestTimestampMixin:
    """Tests for TimestampMixin column definitions."""

    def test_mixin_has_created_at(self) -> None:
        """TimestampMixin should expose a created_at mapped column."""
        assert hasattr(TimestampMixin, "created_at")

    def test_mixin_has_updated_at(self) -> None:
        """TimestampMixin should expose an updated_at mapped column."""
        assert hasattr(TimestampMixin, "updated_at")

    def test_created_at_not_nullable(self) -> None:
        """created_at column should be non-nullable."""
        col = Extension.__table__.columns["created_at"]
        assert col.nullable is False

    def test_updated_at_not_nullable(self) -> None:
        """updated_at column should be non-nullable."""
        col = Extension.__table__.columns["updated_at"]
        assert col.nullable is False


# ---------------------------------------------------------------------------
# Extension model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestExtensionModel:
    """Tests for the Extension ORM model."""

    def test_tablename(self) -> None:
        """Extension.__tablename__ should be 'extensions'."""
        assert Extension.__tablename__ == "extensions"

    def test_primary_key_column(self) -> None:
        """Extension should have an autoincrement integer primary key."""
        col = Extension.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_number_column_unique_not_null(self) -> None:
        """number column should be unique and not nullable."""
        col = Extension.__table__.columns["number"]
        assert col.unique is True
        assert col.nullable is False

    def test_name_column_not_null(self) -> None:
        """name column should not be nullable."""
        col = Extension.__table__.columns["name"]
        assert col.nullable is False

    def test_password_hash_column_not_null(self) -> None:
        """password_hash column should not be nullable."""
        col = Extension.__table__.columns["password_hash"]
        assert col.nullable is False

    def test_email_column_nullable(self) -> None:
        """email column should be nullable."""
        col = Extension.__table__.columns["email"]
        assert col.nullable is True

    def test_voicemail_enabled_defaults_true(self) -> None:
        """voicemail_enabled should default to True."""
        col = Extension.__table__.columns["voicemail_enabled"]
        assert col.server_default is not None
        assert col.server_default.arg == "1"

    def test_is_admin_defaults_false(self) -> None:
        """is_admin should default to False."""
        col = Extension.__table__.columns["is_admin"]
        assert col.server_default.arg == "0"

    def test_dnd_enabled_defaults_false(self) -> None:
        """dnd_enabled should default to False."""
        col = Extension.__table__.columns["dnd_enabled"]
        assert col.server_default.arg == "0"

    def test_forward_enabled_defaults_false(self) -> None:
        """forward_enabled should default to False."""
        col = Extension.__table__.columns["forward_enabled"]
        assert col.server_default.arg == "0"

    def test_forward_destination_nullable(self) -> None:
        """forward_destination should be nullable."""
        col = Extension.__table__.columns["forward_destination"]
        assert col.nullable is True

    def test_allow_external_defaults_true(self) -> None:
        """allow_external should default to True."""
        col = Extension.__table__.columns["allow_external"]
        assert col.server_default.arg == "1"

    def test_ad_synced_defaults_false(self) -> None:
        """ad_synced should default to False."""
        col = Extension.__table__.columns["ad_synced"]
        assert col.server_default.arg == "0"

    def test_registered_defaults_false(self) -> None:
        """registered should default to False."""
        col = Extension.__table__.columns["registered"]
        assert col.server_default.arg == "0"

    def test_registered_at_nullable(self) -> None:
        """registered_at column should be nullable."""
        col = Extension.__table__.columns["registered_at"]
        assert col.nullable is True

    def test_caller_id_nullable(self) -> None:
        """caller_id column should be nullable."""
        col = Extension.__table__.columns["caller_id"]
        assert col.nullable is True

    def test_voicemail_pin_hash_nullable(self) -> None:
        """voicemail_pin_hash should be nullable."""
        col = Extension.__table__.columns["voicemail_pin_hash"]
        assert col.nullable is True

    def test_indexes_defined(self) -> None:
        """Extension table should define expected indexes."""
        index_names = {idx.name for idx in Extension.__table__.indexes}
        assert "ix_extensions_number" in index_names
        assert "ix_extensions_email" in index_names
        assert "ix_extensions_ad_synced" in index_names

    def test_repr(self, db_session: Session) -> None:
        """Extension.__repr__ should include id, number, and name."""
        ext = Extension(
            id=1, number="1001", name="Alice", password_hash="hash123"
        )
        db_session.add(ext)
        db_session.flush()
        result = repr(ext)
        assert "Extension" in result
        assert "1001" in result
        assert "Alice" in result
        assert "id=1" in result
        db_session.rollback()

    def test_repr_different_values(self, db_session: Session) -> None:
        """__repr__ should reflect the actual attribute values."""
        ext = Extension(
            id=42, number="9999", name="Bob", password_hash="hash456"
        )
        db_session.add(ext)
        db_session.flush()
        result = repr(ext)
        assert "id=42" in result
        assert "9999" in result
        assert "Bob" in result
        db_session.rollback()

    def test_inherits_timestamp_mixin(self) -> None:
        """Extension should inherit columns from TimestampMixin."""
        col_names = {c.name for c in Extension.__table__.columns}
        assert "created_at" in col_names
        assert "updated_at" in col_names

    def test_column_count(self) -> None:
        """Extension table should have the expected number of columns."""
        # 16 defined + 2 from TimestampMixin = 18
        col_names = {c.name for c in Extension.__table__.columns}
        assert len(col_names) == 18


# ---------------------------------------------------------------------------
# CallRecord model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCallRecordModel:
    """Tests for the CallRecord ORM model."""

    def test_tablename(self) -> None:
        """CallRecord.__tablename__ should be 'call_records'."""
        assert CallRecord.__tablename__ == "call_records"

    def test_primary_key(self) -> None:
        """CallRecord should have an autoincrement integer primary key."""
        col = CallRecord.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_call_id_unique_not_null(self) -> None:
        """call_id should be unique and not nullable."""
        col = CallRecord.__table__.columns["call_id"]
        assert col.unique is True
        assert col.nullable is False

    def test_caller_not_null(self) -> None:
        """caller column should not be nullable."""
        col = CallRecord.__table__.columns["caller"]
        assert col.nullable is False

    def test_callee_not_null(self) -> None:
        """callee column should not be nullable."""
        col = CallRecord.__table__.columns["callee"]
        assert col.nullable is False

    def test_start_time_nullable(self) -> None:
        """start_time column should be nullable."""
        col = CallRecord.__table__.columns["start_time"]
        assert col.nullable is True

    def test_end_time_nullable(self) -> None:
        """end_time column should be nullable."""
        col = CallRecord.__table__.columns["end_time"]
        assert col.nullable is True

    def test_duration_nullable(self) -> None:
        """duration column should be nullable."""
        col = CallRecord.__table__.columns["duration"]
        assert col.nullable is True

    def test_status_nullable(self) -> None:
        """status column should be nullable."""
        col = CallRecord.__table__.columns["status"]
        assert col.nullable is True

    def test_direction_nullable_and_comment(self) -> None:
        """direction column should be nullable and have a descriptive comment."""
        col = CallRecord.__table__.columns["direction"]
        assert col.nullable is True
        assert col.comment is not None
        assert "inbound" in col.comment

    def test_recording_path_nullable(self) -> None:
        """recording_path should be nullable."""
        col = CallRecord.__table__.columns["recording_path"]
        assert col.nullable is True

    def test_created_at_not_nullable(self) -> None:
        """created_at column should not be nullable."""
        col = CallRecord.__table__.columns["created_at"]
        assert col.nullable is False

    def test_indexes(self) -> None:
        """CallRecord table should define expected indexes."""
        index_names = {idx.name for idx in CallRecord.__table__.indexes}
        assert "ix_call_records_call_id" in index_names
        assert "ix_call_records_caller" in index_names
        assert "ix_call_records_callee" in index_names
        assert "ix_call_records_start_time" in index_names
        assert "ix_call_records_direction" in index_names

    def test_repr(self, db_session: Session) -> None:
        """CallRecord.__repr__ should include id, call_id, caller, callee."""
        record = CallRecord(
            id=10, call_id="abc-123", caller="1001", callee="1002"
        )
        db_session.add(record)
        db_session.flush()
        result = repr(record)
        assert "CallRecord" in result
        assert "abc-123" in result
        assert "1001" in result
        assert "1002" in result
        assert "id=10" in result
        db_session.rollback()

    def test_repr_different_values(self, db_session: Session) -> None:
        """__repr__ should reflect the actual attribute values."""
        record = CallRecord(
            id=99, call_id="xyz-789", caller="2001", callee="3001"
        )
        db_session.add(record)
        db_session.flush()
        result = repr(record)
        assert "id=99" in result
        assert "xyz-789" in result
        db_session.rollback()

    def test_does_not_inherit_timestamp_mixin(self) -> None:
        """CallRecord defines its own created_at, not via TimestampMixin (no updated_at)."""
        col_names = {c.name for c in CallRecord.__table__.columns}
        assert "created_at" in col_names
        assert "updated_at" not in col_names

    def test_column_count(self) -> None:
        """CallRecord table should have the expected number of columns."""
        col_names = {c.name for c in CallRecord.__table__.columns}
        # id, call_id, caller, callee, start_time, end_time, duration,
        # status, direction, recording_path, created_at = 11
        assert len(col_names) == 11


# ---------------------------------------------------------------------------
# Voicemail model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestVoicemailModel:
    """Tests for the Voicemail ORM model."""

    def test_tablename(self) -> None:
        """Voicemail.__tablename__ should be 'voicemails'."""
        assert Voicemail.__tablename__ == "voicemails"

    def test_primary_key(self) -> None:
        """Voicemail should have an autoincrement integer primary key."""
        col = Voicemail.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_extension_not_null(self) -> None:
        """extension column should not be nullable."""
        col = Voicemail.__table__.columns["extension"]
        assert col.nullable is False

    def test_caller_id_nullable(self) -> None:
        """caller_id column should be nullable."""
        col = Voicemail.__table__.columns["caller_id"]
        assert col.nullable is True

    def test_timestamp_not_null(self) -> None:
        """timestamp column should not be nullable."""
        col = Voicemail.__table__.columns["timestamp"]
        assert col.nullable is False

    def test_duration_nullable(self) -> None:
        """duration column should be nullable."""
        col = Voicemail.__table__.columns["duration"]
        assert col.nullable is True

    def test_listened_defaults_false(self) -> None:
        """listened column should default to False."""
        col = Voicemail.__table__.columns["listened"]
        assert col.server_default is not None
        assert col.server_default.arg == "0"

    def test_audio_path_nullable(self) -> None:
        """audio_path column should be nullable."""
        col = Voicemail.__table__.columns["audio_path"]
        assert col.nullable is True

    def test_transcription_text_nullable(self) -> None:
        """transcription_text column should be nullable Text type."""
        col = Voicemail.__table__.columns["transcription_text"]
        assert col.nullable is True

    def test_transcription_confidence_nullable(self) -> None:
        """transcription_confidence column should be nullable Float type."""
        col = Voicemail.__table__.columns["transcription_confidence"]
        assert col.nullable is True

    def test_created_at_not_nullable(self) -> None:
        """created_at column should not be nullable."""
        col = Voicemail.__table__.columns["created_at"]
        assert col.nullable is False

    def test_indexes(self) -> None:
        """Voicemail table should define expected indexes."""
        index_names = {idx.name for idx in Voicemail.__table__.indexes}
        assert "ix_voicemails_extension" in index_names
        assert "ix_voicemails_listened" in index_names
        assert "ix_voicemails_timestamp" in index_names

    def test_repr(self, db_session: Session) -> None:
        """Voicemail.__repr__ should include id, extension, caller_id, listened."""
        vm = Voicemail(
            id=5, extension="1001", caller_id="5551234567", listened=False
        )
        db_session.add(vm)
        db_session.flush()
        result = repr(vm)
        assert "Voicemail" in result
        assert "1001" in result
        assert "5551234567" in result
        assert "listened=False" in result
        assert "id=5" in result
        db_session.rollback()

    def test_repr_listened_true(self, db_session: Session) -> None:
        """__repr__ should show listened=True when message has been played."""
        vm = Voicemail(
            id=6, extension="2002", caller_id=None, listened=True
        )
        db_session.add(vm)
        db_session.flush()
        result = repr(vm)
        assert "listened=True" in result
        assert "2002" in result
        db_session.rollback()

    def test_does_not_inherit_timestamp_mixin(self) -> None:
        """Voicemail defines its own created_at, not via TimestampMixin (no updated_at)."""
        col_names = {c.name for c in Voicemail.__table__.columns}
        assert "created_at" in col_names
        assert "updated_at" not in col_names

    def test_column_count(self) -> None:
        """Voicemail table should have the expected number of columns."""
        col_names = {c.name for c in Voicemail.__table__.columns}
        # id, extension, caller_id, timestamp, duration, listened,
        # audio_path, transcription_text, transcription_confidence, created_at = 10
        assert len(col_names) == 10


# ---------------------------------------------------------------------------
# RegisteredPhone model
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegisteredPhoneModel:
    """Tests for the RegisteredPhone ORM model."""

    def test_tablename(self) -> None:
        """RegisteredPhone.__tablename__ should be 'registered_phones'."""
        assert RegisteredPhone.__tablename__ == "registered_phones"

    def test_primary_key(self) -> None:
        """RegisteredPhone should have an autoincrement integer primary key."""
        col = RegisteredPhone.__table__.columns["id"]
        assert col.primary_key is True
        assert col.autoincrement is True

    def test_extension_not_null(self) -> None:
        """extension column should not be nullable."""
        col = RegisteredPhone.__table__.columns["extension"]
        assert col.nullable is False

    def test_ip_address_not_null(self) -> None:
        """ip_address column should not be nullable."""
        col = RegisteredPhone.__table__.columns["ip_address"]
        assert col.nullable is False

    def test_user_agent_nullable(self) -> None:
        """user_agent column should be nullable."""
        col = RegisteredPhone.__table__.columns["user_agent"]
        assert col.nullable is True

    def test_mac_address_nullable(self) -> None:
        """mac_address column should be nullable."""
        col = RegisteredPhone.__table__.columns["mac_address"]
        assert col.nullable is True

    def test_registered_at_not_nullable(self) -> None:
        """registered_at column should not be nullable."""
        col = RegisteredPhone.__table__.columns["registered_at"]
        assert col.nullable is False

    def test_expires_at_nullable(self) -> None:
        """expires_at column should be nullable."""
        col = RegisteredPhone.__table__.columns["expires_at"]
        assert col.nullable is True

    def test_indexes(self) -> None:
        """RegisteredPhone table should define expected indexes."""
        index_names = {idx.name for idx in RegisteredPhone.__table__.indexes}
        assert "ix_registered_phones_extension" in index_names
        assert "ix_registered_phones_ip_address" in index_names
        assert "ix_registered_phones_mac_address" in index_names

    def test_repr(self, db_session: Session) -> None:
        """RegisteredPhone.__repr__ should include id, extension, ip, mac."""
        phone = RegisteredPhone(
            id=3, extension="1001", ip_address="192.168.1.50",
            mac_address="AA:BB:CC:DD:EE:FF",
        )
        db_session.add(phone)
        db_session.flush()
        result = repr(phone)
        assert "RegisteredPhone" in result
        assert "1001" in result
        assert "192.168.1.50" in result
        assert "AA:BB:CC:DD:EE:FF" in result
        assert "id=3" in result
        db_session.rollback()

    def test_repr_none_mac(self, db_session: Session) -> None:
        """__repr__ should handle None mac_address gracefully."""
        phone = RegisteredPhone(
            id=4, extension="2002", ip_address="10.0.0.1",
            mac_address=None,
        )
        db_session.add(phone)
        db_session.flush()
        result = repr(phone)
        assert "None" in result
        assert "2002" in result
        db_session.rollback()

    def test_does_not_inherit_timestamp_mixin(self) -> None:
        """RegisteredPhone does not use TimestampMixin (no updated_at)."""
        col_names = {c.name for c in RegisteredPhone.__table__.columns}
        assert "updated_at" not in col_names

    def test_column_count(self) -> None:
        """RegisteredPhone table should have the expected number of columns."""
        col_names = {c.name for c in RegisteredPhone.__table__.columns}
        # id, extension, ip_address, user_agent, mac_address,
        # registered_at, expires_at = 7
        assert len(col_names) == 7


# ---------------------------------------------------------------------------
# Cross-model / package tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestModelPackage:
    """Tests for the pbx.models package-level exports."""

    def test_all_models_share_same_base(self) -> None:
        """All models should derive from the same Base class."""
        for model_cls in (Extension, CallRecord, Voicemail, RegisteredPhone):
            assert issubclass(model_cls, Base)

    def test_all_models_have_tablename(self) -> None:
        """Every model should declare a __tablename__."""
        for model_cls in (Extension, CallRecord, Voicemail, RegisteredPhone):
            assert hasattr(model_cls, "__tablename__")
            assert isinstance(model_cls.__tablename__, str)

    def test_all_models_have_repr(self) -> None:
        """Every model should override __repr__."""
        for model_cls in (Extension, CallRecord, Voicemail, RegisteredPhone):
            assert "__repr__" in model_cls.__dict__

    def test_package_exports(self) -> None:
        """The models package __all__ should export all public symbols."""
        from pbx.models import __all__ as exported

        assert "Base" in exported
        assert "TimestampMixin" in exported
        assert "Extension" in exported
        assert "CallRecord" in exported
        assert "Voicemail" in exported
        assert "RegisteredPhone" in exported
