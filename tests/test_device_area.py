"""Regression tests for assigning the configured area to the device.

The config/options flows store an area ID, while
``device_registry.async_get_or_create(suggested_area=...)`` expects an area
*name*. Passing the ID made Home Assistant create a second area named after the
ID (the "Name and assign" dialog then showed that name). The integration now
assigns the area explicitly.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from homeassistant.const import CONF_NAME
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nfc_tasgs import _apply_device_area
from custom_components.nfc_tasgs.const import (
    CONF_ACTIONS,
    CONF_AREA_ID,
    CONF_DEFAULT_ACTION,
    CONF_TAG_ID,
    DOMAIN,
)


@pytest.fixture(autouse=True)
def _enable_custom_integrations(enable_custom_integrations):
    """Load the integration from this repository's custom_components."""
    yield


@pytest.fixture
def expected_lingering_timers() -> bool:
    """The integration schedules its hourly overdue check for the HA lifetime."""
    return True


class FakeAreaRegistry:
    """Minimal area registry exposing only the lookup the helper uses."""

    def __init__(self, areas: dict[str, object]) -> None:
        self._areas = areas

    def async_get_area(self, area_id: str) -> object | None:
        return self._areas.get(area_id)

    def async_get_area_by_name(self, name: str) -> object | None:
        return next(
            (area for area in self._areas.values() if area.name == name),
            None,
        )


class FakeDeviceRegistry:
    """Record area updates instead of touching the real registry."""

    def __init__(self) -> None:
        self.updated: list[tuple[str, dict[str, str]]] = []

    def async_update_device(self, device_id: str, **kwargs: str) -> None:
        self.updated.append((device_id, kwargs))


def _patch_area_registry(monkeypatch, areas: dict[str, object]) -> FakeAreaRegistry:
    area_registry = FakeAreaRegistry(areas)
    monkeypatch.setattr(
        "custom_components.nfc_tasgs.ar.async_get",
        lambda hass: area_registry,
    )
    return area_registry


def test_assigns_the_configured_area(monkeypatch) -> None:
    _patch_area_registry(monkeypatch, {"cozinha": SimpleNamespace(id="cozinha")})
    device_registry = FakeDeviceRegistry()
    device = SimpleNamespace(id="device-1", area_id=None)

    _apply_device_area(object(), device_registry, device, "cozinha")

    assert device_registry.updated == [("device-1", {"area_id": "cozinha"})]


def test_resolves_a_legacy_area_name(monkeypatch) -> None:
    _patch_area_registry(
        monkeypatch, {"cozinha-id": SimpleNamespace(id="cozinha-id", name="Cozinha")}
    )
    device_registry = FakeDeviceRegistry()
    device = SimpleNamespace(id="device-1", area_id=None)

    _apply_device_area(object(), device_registry, device, "Cozinha")

    assert device_registry.updated == [("device-1", {"area_id": "cozinha-id"})]


def test_does_not_rewrite_an_already_correct_area(monkeypatch) -> None:
    _patch_area_registry(monkeypatch, {"cozinha": SimpleNamespace(id="cozinha")})
    device_registry = FakeDeviceRegistry()
    device = SimpleNamespace(id="device-1", area_id="cozinha")

    _apply_device_area(object(), device_registry, device, "cozinha")

    assert device_registry.updated == []


def test_ignores_a_deleted_area(monkeypatch) -> None:
    _patch_area_registry(monkeypatch, {})
    device_registry = FakeDeviceRegistry()
    device = SimpleNamespace(id="device-1", area_id="garage")

    _apply_device_area(object(), device_registry, device, "cozinha")

    assert device_registry.updated == []


def test_ignores_a_blank_area(monkeypatch) -> None:
    _patch_area_registry(monkeypatch, {"cozinha": SimpleNamespace(id="cozinha")})
    device_registry = FakeDeviceRegistry()
    device = SimpleNamespace(id="device-1", area_id="garage")

    _apply_device_area(object(), device_registry, device, "")

    assert device_registry.updated == []


async def test_setup_assigns_the_area_without_creating_a_duplicate(hass) -> None:
    area_registry = ar.async_get(hass)
    # Old-style area IDs are UUIDs, like Cozinha on the live instance. Create
    # one, then rename it so its ID does not match its name.
    area = area_registry.async_create("2dc0ae0069774a2fbe109a6a5c8573cf")
    area = area_registry.async_update(area.id, name="Cozinha")
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Philips Coffee 5400",
        data={
            CONF_NAME: "Philips Coffee 5400",
            CONF_TAG_ID: "tag-id",
            CONF_AREA_ID: area.id,
            CONF_DEFAULT_ACTION: "cleaned",
            CONF_ACTIONS: [
                {
                    "key": "cleaned",
                    "label": "Cleaned",
                    "expected_interval_hours": 168,
                }
            ],
        },
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, entry.entry_id), entry.entry_id
    )
    assert device is not None
    assert device.area_id == area.id

    areas = list(ar.async_get(hass).async_list_areas())
    assert [item.name for item in areas] == ["Cozinha"]
