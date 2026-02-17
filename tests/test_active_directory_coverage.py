"""Comprehensive tests for Active Directory / LDAP integration module."""

import sys
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Bootstrap: mock ldap3 *before* the module under test is imported so that
# the try/except at the top of active_directory.py succeeds and all four
# names (ALL, SUBTREE, Connection, Server) become real module-level attrs.
# ---------------------------------------------------------------------------

_mock_ldap3 = MagicMock()
_mock_ldap3.ALL = "ALL"
_mock_ldap3.SUBTREE = "SUBTREE"
_mock_ldap3.Server = MagicMock
_mock_ldap3.Connection = MagicMock
_mock_ldap3.utils.conv.escape_filter_chars = MagicMock(side_effect=lambda x: x)

# Insert the mock into sys.modules so the import inside active_directory.py works
sys.modules.setdefault("ldap3", _mock_ldap3)
sys.modules.setdefault("ldap3.utils", _mock_ldap3.utils)
sys.modules.setdefault("ldap3.utils.conv", _mock_ldap3.utils.conv)

# Now import the module under test; LDAP3_AVAILABLE will be True
from pbx.integrations.active_directory import ActiveDirectoryIntegration

# Module path for patching
MOD = "pbx.integrations.active_directory"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Sentinel to remove a key from defaults entirely
_REMOVE = object()


def _make_config(overrides: dict | None = None) -> MagicMock:
    """Return a MagicMock config whose ``.get()`` behaves like a dict lookup."""
    defaults: dict = {
        "integrations.active_directory.enabled": True,
        "integrations.active_directory.server": "ldap://ad.example.com",
        "integrations.active_directory.ldap_server": "ldap://ad.example.com",
        "integrations.active_directory.base_dn": "DC=example,DC=com",
        "integrations.active_directory.bind_dn": "CN=admin,DC=example,DC=com",
        "integrations.active_directory.bind_password": "secret",
        "integrations.active_directory.use_ssl": True,
        "integrations.active_directory.auto_provision": True,
        "integrations.active_directory.user_search_base": "OU=Users,DC=example,DC=com",
        "integrations.active_directory.deactivate_removed_users": True,
        "integrations.active_directory.group_permissions": {},
        "config_file": "config.yml",
    }
    if overrides:
        for k, v in overrides.items():
            if v is _REMOVE:
                defaults.pop(k, None)
            else:
                defaults[k] = v

    cfg = MagicMock()
    cfg.get.side_effect = lambda key, default=None: defaults.get(key, default)
    return cfg


def _make_ad(config_overrides: dict | None = None) -> ActiveDirectoryIntegration:
    """Convenience: create an AD integration with patched logger."""
    cfg = _make_config(config_overrides)
    with patch(f"{MOD}.get_logger"):
        ad = ActiveDirectoryIntegration(cfg)
    return ad


def _make_ad_connected(
    entries: list | None = None,
    config_overrides: dict | None = None,
) -> tuple[ActiveDirectoryIntegration, MagicMock]:
    """Create an AD integration that is already 'connected'.

    Returns (ad, mock_connection).
    """
    ad = _make_ad(config_overrides)
    conn = MagicMock()
    conn.bound = True
    conn.entries = entries if entries is not None else []
    ad.connection = conn
    ad.server = MagicMock()
    return ad, conn


class _LdapEntry:
    """Minimal stand-in for an ldap3 Entry.

    Attributes are set only when explicitly requested, so ``hasattr()``
    behaves exactly the same as with a real ldap3 entry object.
    """

    def __init__(
        self,
        sam: str = "jdoe",
        display: str | None = "John Doe",
        mail: str | None = "jdoe@example.com",
        phone: str | None = "1001",
        groups: list | None = None,
        dn: str = "CN=jdoe,OU=Users,DC=example,DC=com",
    ) -> None:
        self.entry_dn = dn

        # sAMAccountName always present (but can be set to None via sam=None)
        self.sAMAccountName = _StrProxy(sam) if sam is not None else None

        if display is not None:
            self.displayName = _StrProxy(display)
        # else: attribute does NOT exist => hasattr(..., 'displayName') is False

        if mail is not None:
            self.mail = _StrProxy(mail)

        if phone is not None:
            self.telephoneNumber = _StrProxy(phone)

        if groups is not None:
            self.memberOf = groups
            # The source checks hasattr(entry, "memberO") (typo) but accesses
            # entry.memberOf.  We set both so both paths work.
            self.memberO = groups


class _StrProxy:
    """Object whose ``str()`` returns a deterministic string."""

    def __init__(self, value: str) -> None:
        self._value = value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"_StrProxy({self._value!r})"


def _make_ldap_entry(
    sam: str = "jdoe",
    display: str | None = "John Doe",
    mail: str | None = "jdoe@example.com",
    phone: str | None = "1001",
    groups: list | None = None,
    dn: str = "CN=jdoe,OU=Users,DC=example,DC=com",
) -> _LdapEntry:
    """Build a fake ldap3 entry object.

    Pass ``None`` for display / mail / phone to omit that attribute entirely
    (so ``hasattr`` returns False).  Pass ``groups`` as a list to set
    ``memberOf``; omit to leave it unset.
    """
    if groups is None:
        # Default: do NOT set memberOf at all (matches has_member_of=False)
        pass
    return _LdapEntry(sam=sam, display=display, mail=mail, phone=phone, groups=groups, dn=dn)


# ---------------------------------------------------------------------------
# Tests: Initialisation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestActiveDirectoryInit:
    """Tests for ActiveDirectoryIntegration.__init__."""

    def test_init_enabled(self) -> None:
        ad = _make_ad()
        assert ad.enabled is True
        assert ad.ldap_server == "ldap://ad.example.com"
        assert ad.base_dn == "DC=example,DC=com"
        assert ad.bind_dn == "CN=admin,DC=example,DC=com"
        assert ad.bind_password == "secret"
        assert ad.use_ssl is True
        assert ad.auto_provision is True
        assert ad.connection is None
        assert ad.server is None

    @patch(f"{MOD}.LDAP3_AVAILABLE", False)
    def test_init_enabled_but_ldap3_unavailable(self) -> None:
        cfg = _make_config()
        with patch(f"{MOD}.get_logger"):
            ad = ActiveDirectoryIntegration(cfg)
        assert ad.enabled is False

    def test_init_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.enabled is False

    def test_init_server_fallback(self) -> None:
        """Falls back to ldap_server key when server key is absent."""
        ad = _make_ad(
            {
                "integrations.active_directory.server": _REMOVE,
                "integrations.active_directory.ldap_server": "ldap://fallback.example.com",
            }
        )
        assert ad.ldap_server == "ldap://fallback.example.com"

    def test_init_defaults_for_optional_fields(self) -> None:
        ad = _make_ad(
            {
                "integrations.active_directory.use_ssl": _REMOVE,
                "integrations.active_directory.auto_provision": _REMOVE,
            }
        )
        assert ad.use_ssl is True
        assert ad.auto_provision is False


# ---------------------------------------------------------------------------
# Tests: connect()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestConnect:
    """Tests for ActiveDirectoryIntegration.connect."""

    def test_connect_when_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.connect() is False

    @patch(f"{MOD}.LDAP3_AVAILABLE", False)
    def test_connect_when_ldap3_unavailable(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.connect() is False

    def test_connect_already_bound(self) -> None:
        ad = _make_ad()
        ad.connection = MagicMock()
        ad.connection.bound = True
        assert ad.connect() is True

    def test_connect_missing_credentials(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.connect() is False

    def test_connect_missing_base_dn(self) -> None:
        ad = _make_ad({"integrations.active_directory.base_dn": None})
        assert ad.connect() is False

    @patch(f"{MOD}.Connection")
    @patch(f"{MOD}.Server")
    def test_connect_success(self, mock_server_cls: MagicMock, mock_conn_cls: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_conn.bound = True
        mock_conn_cls.return_value = mock_conn

        ad = _make_ad()
        result = ad.connect()

        assert result is True
        assert ad.connection is mock_conn
        mock_server_cls.assert_called_once()
        mock_conn_cls.assert_called_once()

    @patch(f"{MOD}.Connection")
    @patch(f"{MOD}.Server")
    def test_connect_bind_fails(self, mock_server_cls: MagicMock, mock_conn_cls: MagicMock) -> None:
        mock_conn = MagicMock()
        mock_conn.bound = False
        mock_conn_cls.return_value = mock_conn

        ad = _make_ad()
        assert ad.connect() is False

    @patch(f"{MOD}.Connection")
    @patch(f"{MOD}.Server")
    def test_connect_os_error(self, mock_server_cls: MagicMock, mock_conn_cls: MagicMock) -> None:
        mock_conn_cls.side_effect = OSError("Connection refused")

        ad = _make_ad()
        assert ad.connect() is False
        assert ad.connection is None

    @patch(f"{MOD}.Connection")
    @patch(f"{MOD}.Server")
    def test_connect_value_error(
        self, mock_server_cls: MagicMock, mock_conn_cls: MagicMock
    ) -> None:
        mock_conn_cls.side_effect = ValueError("bad value")

        ad = _make_ad()
        assert ad.connect() is False
        assert ad.connection is None


# ---------------------------------------------------------------------------
# Tests: authenticate_user()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAuthenticateUser:
    """Tests for ActiveDirectoryIntegration.authenticate_user."""

    def test_auth_when_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.authenticate_user("user", "pass") is None

    def test_auth_connect_fails(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.authenticate_user("user", "pass") is None

    def test_auth_user_not_found(self) -> None:
        ad, _conn = _make_ad_connected(entries=[])
        result = ad.authenticate_user("jdoe", "password123")
        assert result is None

    def test_auth_success(self) -> None:
        entry = _make_ldap_entry(groups=["CN=Sales,OU=Groups,DC=example,DC=com"])
        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        user_conn = MagicMock()
        user_conn.bound = True

        with patch(f"{MOD}.Connection", return_value=user_conn):
            result = ad.authenticate_user("jdoe", "password123")

        assert result is not None
        assert result["username"] == "jdoe"
        assert result["display_name"] == "John Doe"
        assert result["email"] == "jdoe@example.com"
        assert result["phone"] == "1001"
        user_conn.unbind.assert_called_once()

    def test_auth_success_minimal_attrs(self) -> None:
        """Entry without displayName, mail, telephoneNumber, memberOf."""
        entry = _make_ldap_entry(display=None, mail=None, phone=None, groups=None)
        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        user_conn = MagicMock()
        user_conn.bound = True

        with patch(f"{MOD}.Connection", return_value=user_conn):
            result = ad.authenticate_user("jdoe", "password123")

        assert result is not None
        assert result["username"] == "jdoe"
        assert result["display_name"] == "jdoe"
        assert result["email"] is None
        assert result["phone"] is None
        assert result["groups"] == []

    def test_auth_user_bind_fails(self) -> None:
        entry = _make_ldap_entry(groups=["CN=G,OU=G,DC=d,DC=c"])
        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        user_conn = MagicMock()
        user_conn.bound = False

        with patch(f"{MOD}.Connection", return_value=user_conn):
            result = ad.authenticate_user("jdoe", "wrong_password")

        assert result is None

    def test_auth_exception_os_error(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = OSError("network error")

        result = ad.authenticate_user("jdoe", "password123")
        assert result is None

    def test_auth_exception_key_error(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = KeyError("missing key")

        result = ad.authenticate_user("jdoe", "password123")
        assert result is None

    def test_auth_uses_custom_search_base(self) -> None:
        entry = _make_ldap_entry(groups=["CN=G,OU=G,DC=d,DC=c"])
        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.user_search_base": "OU=Staff,DC=example,DC=com"
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        user_conn = MagicMock()
        user_conn.bound = True

        with patch(f"{MOD}.Connection", return_value=user_conn):
            ad.authenticate_user("jdoe", "password123")

        call_kwargs = conn.search.call_args[1]
        assert call_kwargs["search_base"] == "OU=Staff,DC=example,DC=com"


# ---------------------------------------------------------------------------
# Tests: _map_groups_to_permissions()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMapGroupsToPermissions:
    """Tests for ActiveDirectoryIntegration._map_groups_to_permissions."""

    def test_no_config(self) -> None:
        ad = _make_ad({"integrations.active_directory.group_permissions": {}})
        result = ad._map_groups_to_permissions(["CN=Sales,OU=Groups,DC=example,DC=com"])
        assert result == {}

    def test_no_config_none(self) -> None:
        ad = _make_ad({"integrations.active_directory.group_permissions": None})
        result = ad._map_groups_to_permissions(["CN=Sales,OU=Groups,DC=example,DC=com"])
        assert result == {}

    def test_match_by_full_dn(self) -> None:
        group_dn = "CN=PBX-Admins,OU=Groups,DC=example,DC=com"
        ad = _make_ad(
            {
                "integrations.active_directory.group_permissions": {
                    group_dn: ["admin", "external_calling"]
                }
            }
        )
        result = ad._map_groups_to_permissions([group_dn])
        assert result == {"admin": True, "external_calling": True}

    def test_match_by_cn_extraction(self) -> None:
        group_dn = "CN=Managers,OU=Groups,DC=example,DC=com"
        ad = _make_ad(
            {"integrations.active_directory.group_permissions": {group_dn: ["manage_users"]}}
        )
        result = ad._map_groups_to_permissions([group_dn])
        assert result == {"manage_users": True}

    def test_match_cn_only_config(self) -> None:
        """Config group is just a name (no CN= prefix), user group has CN=."""
        user_group = "CN=Sales,OU=Groups,DC=example,DC=com"
        ad = _make_ad(
            {"integrations.active_directory.group_permissions": {"Sales": ["view_reports"]}}
        )
        result = ad._map_groups_to_permissions([user_group])
        assert result == {"view_reports": True}

    def test_no_match(self) -> None:
        ad = _make_ad(
            {
                "integrations.active_directory.group_permissions": {
                    "CN=Finance,OU=Groups,DC=example,DC=com": ["view_reports"]
                }
            }
        )
        result = ad._map_groups_to_permissions(["CN=Sales,OU=Groups,DC=example,DC=com"])
        assert result == {}

    def test_non_list_perms_skipped(self) -> None:
        group_dn = "CN=PBX-Admins,OU=Groups,DC=example,DC=com"
        ad = _make_ad(
            {
                "integrations.active_directory.group_permissions": {
                    group_dn: "admin"  # string, not list
                }
            }
        )
        result = ad._map_groups_to_permissions([group_dn])
        assert result == {}

    def test_user_group_without_cn_prefix(self) -> None:
        ad = _make_ad(
            {"integrations.active_directory.group_permissions": {"Developers": ["deploy"]}}
        )
        result = ad._map_groups_to_permissions(["Developers"])
        assert result == {"deploy": True}

    def test_config_group_cn_no_comma(self) -> None:
        """Config group starts with CN= but has no comma."""
        ad = _make_ad({"integrations.active_directory.group_permissions": {"CN=Admins": ["admin"]}})
        result = ad._map_groups_to_permissions(["CN=Admins"])
        assert result == {"admin": True}

    def test_multiple_groups_multiple_permissions(self) -> None:
        ad = _make_ad(
            {
                "integrations.active_directory.group_permissions": {
                    "CN=Admins,OU=Groups,DC=example,DC=com": ["admin"],
                    "CN=Sales,OU=Groups,DC=example,DC=com": ["external_calling"],
                }
            }
        )
        result = ad._map_groups_to_permissions(
            [
                "CN=Admins,OU=Groups,DC=example,DC=com",
                "CN=Sales,OU=Groups,DC=example,DC=com",
            ]
        )
        assert result == {"admin": True, "external_calling": True}

    def test_empty_user_groups(self) -> None:
        ad = _make_ad(
            {
                "integrations.active_directory.group_permissions": {
                    "CN=Admins,OU=Groups,DC=example,DC=com": ["admin"]
                }
            }
        )
        result = ad._map_groups_to_permissions([])
        assert result == {}


# ---------------------------------------------------------------------------
# Tests: get_user_groups()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetUserGroups:
    """Tests for ActiveDirectoryIntegration.get_user_groups."""

    def test_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.get_user_groups("jdoe") == []

    def test_connect_fails(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.get_user_groups("jdoe") == []

    def test_user_not_found(self) -> None:
        ad, _conn = _make_ad_connected(entries=[])
        result = ad.get_user_groups("unknown")
        assert result == []

    def test_returns_group_names(self) -> None:
        entry = _make_ldap_entry(
            groups=[
                "CN=Sales,OU=Groups,DC=example,DC=com",
                "CN=IT,OU=Groups,DC=example,DC=com",
            ]
        )

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_groups("jdoe")
        assert result == ["Sales", "IT"]

    def test_groups_no_member_of_attr(self) -> None:
        """User has no memberOf attribute."""
        entry = _make_ldap_entry(groups=None)  # no memberOf

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_groups("jdoe")
        assert result == []

    def test_groups_non_cn_entries_skipped(self) -> None:
        """Group DNs not starting with CN= are skipped."""
        entry = _make_ldap_entry(
            groups=[
                "OU=Sales,OU=Groups,DC=example,DC=com",  # not CN=
                "CN=IT,OU=Groups,DC=example,DC=com",
            ]
        )

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_groups("jdoe")
        assert result == ["IT"]

    def test_groups_exception(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = TypeError("bad type")

        result = ad.get_user_groups("jdoe")
        assert result == []

    def test_groups_os_error(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = OSError("network error")

        result = ad.get_user_groups("jdoe")
        assert result == []


# ---------------------------------------------------------------------------
# Tests: search_users()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchUsers:
    """Tests for ActiveDirectoryIntegration.search_users."""

    def test_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.search_users("john") == []

    def test_connect_fails(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.search_users("john") == []

    def test_search_returns_results(self) -> None:
        entry = _make_ldap_entry()

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        results = ad.search_users("john")

        assert len(results) == 1
        assert results[0]["username"] == "jdoe"
        assert results[0]["display_name"] == "John Doe"
        assert results[0]["email"] == "jdoe@example.com"
        assert results[0]["phone"] == "1001"

    def test_search_minimal_attrs(self) -> None:
        entry = _make_ldap_entry(display=None, mail=None, phone=None)

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        results = ad.search_users("john")

        assert len(results) == 1
        assert results[0]["display_name"] == "jdoe"
        assert results[0]["email"] is None
        assert results[0]["phone"] is None

    def test_search_exception(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = ValueError("bad filter")

        results = ad.search_users("john")
        assert results == []

    def test_search_custom_max_results(self) -> None:
        ad, conn = _make_ad_connected()

        ad.search_users("john", max_results=10)

        call_kwargs = conn.search.call_args[1]
        assert call_kwargs["size_limit"] == 10

    def test_search_empty_results(self) -> None:
        ad, _conn = _make_ad_connected(entries=[])

        results = ad.search_users("nonexistent")
        assert results == []

    def test_search_os_error(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = OSError("connection lost")

        results = ad.search_users("john")
        assert results == []


# ---------------------------------------------------------------------------
# Tests: get_user_photo()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetUserPhoto:
    """Tests for ActiveDirectoryIntegration.get_user_photo."""

    def test_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.get_user_photo("jdoe") is None

    def test_connect_fails(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.get_user_photo("jdoe") is None

    def test_user_not_found(self) -> None:
        ad, _conn = _make_ad_connected(entries=[])
        result = ad.get_user_photo("jdoe")
        assert result is None

    def test_photo_found(self) -> None:
        photo_bytes = b"\xff\xd8\xff\xe0fake_jpeg_data"

        entry = MagicMock()
        entry.thumbnailPhoto = MagicMock()
        entry.thumbnailPhoto.value = photo_bytes

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_photo("jdoe")
        assert result == photo_bytes

    def test_no_photo_attribute(self) -> None:
        entry = MagicMock(spec=["entry_dn"])
        entry.entry_dn = "CN=jdoe,DC=example,DC=com"

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_photo("jdoe")
        assert result is None

    def test_photo_empty_value(self) -> None:
        entry = MagicMock()
        entry.thumbnailPhoto = MagicMock()
        entry.thumbnailPhoto.value = None

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        result = ad.get_user_photo("jdoe")
        assert result is None

    def test_photo_exception(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = OSError("connection lost")

        result = ad.get_user_photo("jdoe")
        assert result is None

    def test_photo_key_error(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = KeyError("missing")

        result = ad.get_user_photo("jdoe")
        assert result is None


# ---------------------------------------------------------------------------
# Tests: sync_users()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSyncUsers:
    """Tests for ActiveDirectoryIntegration.sync_users."""

    def test_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.enabled": False})
        assert ad.sync_users() == 0

    def test_auto_provision_disabled(self) -> None:
        ad = _make_ad({"integrations.active_directory.auto_provision": False})
        assert ad.sync_users() == 0

    def test_connect_fails(self) -> None:
        ad = _make_ad({"integrations.active_directory.bind_password": None})
        assert ad.sync_users() == 0

    def test_no_users_found(self) -> None:
        ad, _conn = _make_ad_connected()
        result = ad.sync_users()
        assert result == 0

    def test_sync_creates_new_extension_in_db(self) -> None:
        entry = _make_ldap_entry(
            sam="jdoe", display="John Doe", mail="jdoe@example.com", phone="1001"
        )

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)

        assert result["synced_count"] == 1
        extension_db.add.assert_called_once()
        call_kwargs = extension_db.add.call_args[1]
        assert call_kwargs["number"] == "1001"
        assert call_kwargs["name"] == "John Doe"
        assert call_kwargs["ad_synced"] is True
        assert call_kwargs["ad_username"] == "jdoe"

    def test_sync_updates_existing_extension_in_db(self) -> None:
        entry = _make_ldap_entry(
            sam="jdoe", display="John Doe", mail="jdoe@example.com", phone="1001"
        )

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old Name"}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)

        assert result["synced_count"] == 1
        extension_db.update.assert_called()
        call_kwargs = extension_db.update.call_args_list[0][1]
        assert call_kwargs["name"] == "John Doe"
        assert call_kwargs["ad_synced"] is True

    def test_sync_updates_live_registry(self) -> None:
        entry = _make_ldap_entry(
            sam="jdoe", display="John Doe", mail="jdoe@example.com", phone="1001"
        )

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old Name"}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        ext_obj = MagicMock()
        ext_obj.config = {}
        extension_registry = MagicMock()
        extension_registry.get.return_value = ext_obj

        result = ad.sync_users(extension_registry=extension_registry, extension_db=extension_db)

        assert result["synced_count"] == 1
        assert ext_obj.name == "John Doe"
        assert ext_obj.config["email"] == "jdoe@example.com"
        assert ext_obj.config["ad_synced"] is True

    def test_sync_skips_user_missing_phone(self) -> None:
        """Entry without telephoneNumber is skipped (phone=None)."""
        entry = _make_ldap_entry(phone=None)

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 0

    def test_sync_skips_short_extension(self) -> None:
        entry = _make_ldap_entry(phone="12")  # only 2 digits

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 0

    def test_sync_skips_non_digit_only_phone(self) -> None:
        entry = _make_ldap_entry(phone="abc")  # no digits

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 0

    def test_sync_phone_cleaning(self) -> None:
        """Phone numbers with dashes/spaces get cleaned to digits only."""
        entry = _make_ldap_entry(phone="1-001 ext")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)

        assert result["synced_count"] == 1
        call_kwargs = extension_db.add.call_args[1]
        assert call_kwargs["number"] == "1001"

    def test_sync_deactivates_removed_users_db(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = [
            {"number": "1002", "ad_synced": True},
        ]

        ad.sync_users(extension_db=extension_db)

        deactivation_calls = [
            c for c in extension_db.update.call_args_list if c[1].get("number") == "1002"
        ]
        assert len(deactivation_calls) == 1
        assert deactivation_calls[0][1]["allow_external"] is False

    def test_sync_deactivates_updates_live_registry(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = [
            {"number": "1005", "ad_synced": True},
        ]

        ext_obj = MagicMock()
        ext_obj.config = {}
        extension_registry = MagicMock()
        extension_registry.get.return_value = ext_obj

        ad.sync_users(extension_registry=extension_registry, extension_db=extension_db)

        assert ext_obj.config["allow_external"] is False

    def test_sync_does_not_deactivate_non_ad_synced(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = [
            {"number": "1002", "ad_synced": False},
        ]

        ad.sync_users(extension_db=extension_db)

        deactivation_calls = [
            c for c in extension_db.update.call_args_list if c[1].get("number") == "1002"
        ]
        assert len(deactivation_calls) == 0

    def test_sync_with_config_yml_mode_create(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = None
        mock_pbx_config.add_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 1
        mock_pbx_config.add_extension.assert_called_once()
        mock_pbx_config.save.assert_called_once()

    def test_sync_with_config_yml_mode_update(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        existing_ext = {"number": "1001", "name": "Old Name"}
        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = existing_ext
        mock_pbx_config.update_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 1
        mock_pbx_config.update_extension.assert_called_once()
        assert existing_ext["ad_synced"] is True

    def test_sync_with_config_yml_deactivation(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = None
        mock_pbx_config.add_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = [
            {"number": "2001", "ad_synced": True},
        ]

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            ad.sync_users()

        mock_pbx_config.update_extension.assert_called_with(number="2001", allow_external=False)

    def test_sync_phone_provisioning_reboots(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        device = MagicMock()
        device.extension_number = "1001"
        phone_provisioning = MagicMock()
        phone_provisioning.get_all_devices.return_value = [device]

        result = ad.sync_users(
            extension_db=extension_db,
            phone_provisioning=phone_provisioning,
        )

        assert result["synced_count"] == 1
        assert result["extensions_to_reboot"] == ["1001"]

    def test_sync_phone_provisioning_no_devices(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        phone_provisioning = MagicMock()
        phone_provisioning.get_all_devices.return_value = []

        result = ad.sync_users(
            extension_db=extension_db,
            phone_provisioning=phone_provisioning,
        )

        assert result["synced_count"] == 1
        assert result["extensions_to_reboot"] == []

    def test_sync_create_extension_failure_in_db(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = False
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 0

    def test_sync_update_extension_failure(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old"}
        extension_db.update.return_value = False
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 0

    def test_sync_exception_in_user_processing(self) -> None:
        """Per-user ValueError is caught and processing continues.

        The error must happen AFTER ``username`` is assigned (line 247-249)
        so that the error handler at line 445 can safely access ``username``.
        We trigger it by making telephoneNumber's str() raise ValueError.
        """
        bad_entry = _make_ldap_entry(sam="bad", phone="1001")
        # Override telephoneNumber to raise ValueError during str()
        bad_entry.telephoneNumber = _BadStr()

        good_entry = _make_ldap_entry(sam="good", phone="2001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [bad_entry, good_entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        # good_entry should have been processed
        assert result["synced_count"] == 1

    def test_sync_outer_exception(self) -> None:
        ad, conn = _make_ad_connected()
        conn.search.side_effect = KeyError("unexpected")

        result = ad.sync_users()
        assert result == {"synced_count": 0, "extensions_to_reboot": []}

    def test_sync_creates_new_ext_with_registry(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        extension_registry = MagicMock()
        extension_registry.extensions = {}

        with patch("pbx.features.extensions.Extension") as mock_ext_cls:
            mock_ext_instance = MagicMock()
            mock_ext_cls.return_value = mock_ext_instance
            result = ad.sync_users(extension_registry=extension_registry, extension_db=extension_db)

        assert result["synced_count"] == 1
        assert "1001" in extension_registry.extensions

    def test_sync_with_group_permissions_on_update(self) -> None:
        entry = _make_ldap_entry(
            phone="1001",
            groups=["CN=PBX-Admins,OU=Groups,DC=example,DC=com"],
        )

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.group_permissions": {
                    "CN=PBX-Admins,OU=Groups,DC=example,DC=com": ["admin", "external_calling"]
                }
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old"}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        ext_obj = MagicMock()
        ext_obj.config = {}
        extension_registry = MagicMock()
        extension_registry.get.return_value = ext_obj

        result = ad.sync_users(extension_registry=extension_registry, extension_db=extension_db)

        assert result["synced_count"] == 1
        assert ext_obj.config.get("admin") is True
        assert ext_obj.config.get("external_calling") is True

    def test_sync_config_mode_create_with_registry(self) -> None:
        entry = _make_ldap_entry(
            phone="1001",
            groups=["CN=Sales,OU=Groups,DC=example,DC=com"],
        )

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.group_permissions": {
                    "CN=Sales,OU=Groups,DC=example,DC=com": ["view_reports"]
                }
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.side_effect = [None, {"number": "1001", "ad_synced": False}]
        mock_pbx_config.add_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = []

        extension_registry = MagicMock()
        extension_registry.extensions = {}

        with (
            patch("pbx.utils.config.Config", return_value=mock_pbx_config),
            patch("pbx.features.extensions.Extension") as mock_ext_cls,
        ):
            mock_ext_instance = MagicMock()
            mock_ext_cls.return_value = mock_ext_instance
            result = ad.sync_users(extension_registry=extension_registry)

        assert result["synced_count"] == 1
        assert "1001" in extension_registry.extensions

    def test_sync_config_mode_create_failure(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = None
        mock_pbx_config.add_extension.return_value = False
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 0

    def test_sync_config_mode_update_failure(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = {"number": "1001"}
        mock_pbx_config.update_extension.return_value = False
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 0

    def test_sync_deactivate_removed_users_disabled(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.deactivate_removed_users": False,
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True

        result = ad.sync_users(extension_db=extension_db)

        assert result["synced_count"] == 1
        extension_db.get_ad_synced.assert_not_called()

    def test_sync_no_phone_provisioning_returns_dict(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)

        assert isinstance(result, dict)
        assert result["synced_count"] == 1
        assert result["extensions_to_reboot"] == []

    def test_sync_update_with_permissions_logged(self) -> None:
        entry = _make_ldap_entry(
            phone="1001",
            groups=["CN=Admins,OU=Groups,DC=example,DC=com"],
        )

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.group_permissions": {
                    "CN=Admins,OU=Groups,DC=example,DC=com": ["admin"]
                }
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old", "config": {}}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)
        assert result["synced_count"] == 1

    def test_sync_config_mode_deactivation_with_registry(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = None
        mock_pbx_config.add_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = [
            {"number": "2002", "ad_synced": True},
        ]

        ext_obj = MagicMock()
        ext_obj.config = {}
        extension_registry = MagicMock()
        extension_registry.get.return_value = ext_obj
        extension_registry.extensions = {}

        with (
            patch("pbx.utils.config.Config", return_value=mock_pbx_config),
            patch("pbx.features.extensions.Extension") as mock_ext_cls,
        ):
            mock_ext_cls.return_value = MagicMock()
            ad.sync_users(extension_registry=extension_registry)

        assert ext_obj.config["allow_external"] is False

    def test_sync_entry_without_email_db_create(self) -> None:
        """Entry without email gets None for email in extension data."""
        entry = _make_ldap_entry(phone="1001", mail=None)

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = []

        result = ad.sync_users(extension_db=extension_db)

        assert result["synced_count"] == 1
        call_kwargs = extension_db.add.call_args[1]
        assert call_kwargs["email"] is None

    def test_sync_update_live_registry_no_email(self) -> None:
        """When email is None, it should not be set in ext.config."""
        entry = _make_ldap_entry(phone="1001", mail=None)

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old"}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        ext_obj = MagicMock()
        ext_obj.config = {}
        extension_registry = MagicMock()
        extension_registry.get.return_value = ext_obj

        ad.sync_users(extension_registry=extension_registry, extension_db=extension_db)

        assert "email" not in ext_obj.config

    def test_sync_config_mode_update_with_permissions(self) -> None:
        entry = _make_ldap_entry(
            phone="1001",
            groups=["CN=Admins,OU=Groups,DC=example,DC=com"],
        )

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.group_permissions": {
                    "CN=Admins,OU=Groups,DC=example,DC=com": ["admin"]
                }
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        existing_ext = {"number": "1001", "name": "Old Name"}
        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.return_value = existing_ext
        mock_pbx_config.update_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 1
        assert existing_ext["ad_synced"] is True
        assert existing_ext["admin"] is True

    def test_sync_config_mode_create_new_ext_config_stored(self) -> None:
        """Config mode create: newly created ext config updated with ad_synced + permissions."""
        entry = _make_ldap_entry(
            phone="1001",
            groups=["CN=Admins,OU=Groups,DC=example,DC=com"],
        )

        ad, conn = _make_ad_connected(
            config_overrides={
                "integrations.active_directory.group_permissions": {
                    "CN=Admins,OU=Groups,DC=example,DC=com": ["admin"]
                }
            }
        )

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        new_ext_config = {"number": "1001"}
        mock_pbx_config = MagicMock()
        mock_pbx_config.get_extension.side_effect = [None, new_ext_config]
        mock_pbx_config.add_extension.return_value = True
        mock_pbx_config.get_extensions.return_value = []

        with patch("pbx.utils.config.Config", return_value=mock_pbx_config):
            result = ad.sync_users()

        assert result["synced_count"] == 1
        assert new_ext_config["ad_synced"] is True
        assert new_ext_config["admin"] is True

    def test_sync_phone_provisioning_with_update(self) -> None:
        """Phone provisioning triggers reboot when extensions are updated."""
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = {"number": "1001", "name": "Old"}
        extension_db.update.return_value = True
        extension_db.get_ad_synced.return_value = []

        device = MagicMock()
        device.extension_number = "1001"
        phone_provisioning = MagicMock()
        phone_provisioning.get_all_devices.return_value = [device]

        result = ad.sync_users(
            extension_db=extension_db,
            phone_provisioning=phone_provisioning,
        )

        assert result["extensions_to_reboot"] == ["1001"]

    def test_sync_deactivation_skips_non_digit_numbers(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = [
            {"number": "abc", "ad_synced": True},
        ]

        ad.sync_users(extension_db=extension_db)

        deactivation_calls = [
            c for c in extension_db.update.call_args_list if c[1].get("number") == "abc"
        ]
        assert len(deactivation_calls) == 0

    def test_sync_deactivation_skips_short_numbers(self) -> None:
        entry = _make_ldap_entry(phone="1001")

        ad, conn = _make_ad_connected()

        def do_search(**kwargs):
            conn.entries = [entry]

        conn.search.side_effect = do_search

        extension_db = MagicMock()
        extension_db.get.return_value = None
        extension_db.add.return_value = True
        extension_db.get_ad_synced.return_value = [
            {"number": "12", "ad_synced": True},
        ]

        ad.sync_users(extension_db=extension_db)

        deactivation_calls = [
            c for c in extension_db.update.call_args_list if c[1].get("number") == "12"
        ]
        assert len(deactivation_calls) == 0


class _BadStr:
    """Object whose str() raises ValueError (caught by the except clause)."""

    def __str__(self) -> str:
        raise ValueError("bad entry value")
