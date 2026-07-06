"""Tests for StatisticsController's thin wiring between service and panel."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from app.ui.controllers.statistics_controller import StatisticsController


class FakeStatisticsService:
    def __init__(self, overview: str = "overview") -> None:
        self._overview = overview
        self.compute_calls = 0

    def compute_overview(self) -> str:
        self.compute_calls += 1
        return self._overview


class FakeStatisticsPanel:
    def __init__(self) -> None:
        self.shown_overviews: list[str] = []
        self.bulk_card_running_calls: list[bool] = []
        self.bulk_sealed_running_calls: list[bool] = []

    def show_overview(self, overview: str) -> None:
        self.shown_overviews.append(overview)

    def set_bulk_update_running(self, running: bool) -> None:
        self.bulk_card_running_calls.append(running)

    def set_sealed_bulk_update_running(self, running: bool) -> None:
        self.bulk_sealed_running_calls.append(running)


def test_refresh_computes_and_renders_the_overview() -> None:
    panel = FakeStatisticsPanel()
    service = FakeStatisticsService(overview="the overview")
    controller = StatisticsController(panel, service)

    controller.refresh()

    assert service.compute_calls == 1
    assert panel.shown_overviews == ["the overview"]


def test_set_bulk_card_update_running_forwards_to_panel() -> None:
    panel = FakeStatisticsPanel()
    controller = StatisticsController(panel, FakeStatisticsService())

    controller.set_bulk_card_update_running(True)
    controller.set_bulk_card_update_running(False)

    assert panel.bulk_card_running_calls == [True, False]


def test_set_bulk_sealed_update_running_forwards_to_panel() -> None:
    panel = FakeStatisticsPanel()
    controller = StatisticsController(panel, FakeStatisticsService())

    controller.set_bulk_sealed_update_running(True)
    controller.set_bulk_sealed_update_running(False)

    assert panel.bulk_sealed_running_calls == [True, False]
