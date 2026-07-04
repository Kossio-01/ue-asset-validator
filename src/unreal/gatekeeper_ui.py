"""Artist-friendly Unreal UI for the Gatekeeper validator."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import unreal

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def _load_qt_modules():
    for module_name in ("PySide6", "PySide2"):
        try:
            importlib.import_module(module_name)
            QtCore = importlib.import_module(f"{module_name}.QtCore")
            QtGui = importlib.import_module(f"{module_name}.QtGui")
            QtWidgets = importlib.import_module(f"{module_name}.QtWidgets")
            return QtCore, QtGui, QtWidgets
        except (ModuleNotFoundError, AttributeError):
            continue
    return None, None, None


QtCore, QtGui, QtWidgets = _load_qt_modules()

from core import get_selected_level_actors, run_naming_validation

if QtCore is not None:
    _qt = QtCore.Qt
    WINDOW_STAYS_ON_TOP = getattr(getattr(_qt, "WindowType", _qt), "WindowStaysOnTopHint", getattr(_qt, "WindowStaysOnTopHint", 0))
    ALIGN_LEFT = getattr(getattr(_qt, "AlignmentFlag", _qt), "AlignLeft", getattr(_qt, "AlignLeft", 0))
    POINTING_HAND = getattr(getattr(_qt, "CursorShape", _qt), "PointingHandCursor", getattr(_qt, "PointingHandCursor", 0))
else:
    WINDOW_STAYS_ON_TOP = 0
    ALIGN_LEFT = 0
    POINTING_HAND = 0


class GatekeeperWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GatekeeperWindow")
        self.setWindowTitle("Gatekeeper - Name Validation")
        self.setMinimumSize(900, 620)
        self.setWindowFlags(self.windowFlags() | WINDOW_STAYS_ON_TOP)

        self._summary = None
        self._last_selection_signature = None

        self._build_ui()
        self._apply_styles()
        self._set_empty_state()
        self._start_live_selection_updates()

    def _build_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(14, 14, 14, 14)
        main_layout.setSpacing(12)

        self.header_panel = QtWidgets.QFrame()
        self.header_panel.setObjectName("HeaderPanel")
        header_layout = QtWidgets.QVBoxLayout(self.header_panel)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(6)

        self.title_label = QtWidgets.QLabel("Gatekeeper - Name Validation")
        self.title_label.setObjectName("TitleLabel")
        self.subtitle_label = QtWidgets.QLabel(
            "Helps designers quickly verify the naming of selected static meshes without opening the log."
        )
        self.subtitle_label.setWordWrap(True)
        self.status_label = QtWidgets.QLabel("Ready to inspect the current selection.")
        self.status_label.setObjectName("StatusPill")

        header_layout.addWidget(self.title_label)
        header_layout.addWidget(self.subtitle_label)
        header_layout.addWidget(self.status_label, alignment=ALIGN_LEFT)
        main_layout.addWidget(self.header_panel)

        self.body_panel = QtWidgets.QFrame()
        self.body_panel.setObjectName("BodyPanel")
        body_layout = QtWidgets.QHBoxLayout(self.body_panel)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(14)

        self.left_panel = QtWidgets.QFrame()
        self.left_panel.setObjectName("LeftPanel")
        left_layout = QtWidgets.QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(14, 14, 14, 14)
        left_layout.setSpacing(8)

        left_header = QtWidgets.QVBoxLayout()
        self.left_title = QtWidgets.QLabel("Selection Snapshot")
        self.left_title.setObjectName("SectionTitle")
        self.left_subtitle = QtWidgets.QLabel(
            "This area mirrors your current selection in real time. Pick actors in the Outliner and their names will appear here."
        )
        self.left_subtitle.setObjectName("SectionDescription")
        self.left_subtitle.setWordWrap(True)
        left_header.addWidget(self.left_title)
        left_header.addWidget(self.left_subtitle)
        left_layout.addLayout(left_header)

        self.selection_list = QtWidgets.QListWidget()
        self.selection_list.setObjectName("SelectionList")
        self.selection_list.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.selection_list.setSpacing(6)
        left_layout.addWidget(self.selection_list, stretch=1)

        body_layout.addWidget(self.left_panel, stretch=3)

        self.right_panel = QtWidgets.QFrame()
        self.right_panel.setObjectName("RightPanel")
        right_layout = QtWidgets.QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.summary_card = QtWidgets.QFrame()
        self.summary_card.setObjectName("SummaryCard")
        summary_layout = QtWidgets.QVBoxLayout(self.summary_card)
        summary_layout.setContentsMargins(14, 12, 14, 12)
        summary_layout.setSpacing(8)

        self.summary_title = QtWidgets.QLabel("Selection Summary")
        self.summary_title.setObjectName("SectionTitle")
        self.summary_text = QtWidgets.QLabel(
            "0 actors selected\n0 StaticMesh actors validated\n0 items need attention"
        )
        self.summary_text.setObjectName("SummaryText")
        self.summary_text.setWordWrap(True)
        summary_layout.addWidget(self.summary_title)
        summary_layout.addWidget(self.summary_text)

        self.cards_row = QtWidgets.QHBoxLayout()
        self.cards_row.setSpacing(8)
        self.total_card, self.total_value = self._create_stat_card("Selected")
        self.passed_card, self.passed_value = self._create_stat_card("Passed")
        self.flagged_card, self.flagged_value = self._create_stat_card("Needs Review")
        self.cards_row.addWidget(self.total_card)
        self.cards_row.addWidget(self.passed_card)
        self.cards_row.addWidget(self.flagged_card)
        summary_layout.addLayout(self.cards_row)

        right_layout.addWidget(self.summary_card)

        self.actions_card = QtWidgets.QFrame()
        self.actions_card.setObjectName("ActionsCard")
        actions_layout = QtWidgets.QVBoxLayout(self.actions_card)
        actions_layout.setContentsMargins(14, 12, 14, 12)
        actions_layout.setSpacing(8)

        self.actions_title = QtWidgets.QLabel("Quick Action")
        self.actions_title.setObjectName("SectionTitle")
        self.actions_description = QtWidgets.QLabel(
            "Run the check on the current selection. The result is shown visually below, with no need to read the console."
        )
        self.actions_description.setWordWrap(True)
        self.actions_description.setObjectName("SectionDescription")

        self.btn_validate = QtWidgets.QPushButton("Analyze selection")
        self.btn_validate.setCursor(QtGui.QCursor(POINTING_HAND))
        self.btn_validate.clicked.connect(self.run_naming_audit)

        self.btn_clear = QtWidgets.QPushButton("Clear")
        self.btn_clear.clicked.connect(self.clear_results)

        actions_layout.addWidget(self.actions_title)
        actions_layout.addWidget(self.actions_description)
        actions_layout.addWidget(self.btn_validate)
        actions_layout.addWidget(self.btn_clear)
        right_layout.addWidget(self.actions_card)

        self.report_card = QtWidgets.QFrame()
        self.report_card.setObjectName("ReportCard")
        report_layout = QtWidgets.QVBoxLayout(self.report_card)
        report_layout.setContentsMargins(14, 12, 14, 12)
        report_layout.setSpacing(8)

        self.report_title = QtWidgets.QLabel("Results & Report")
        self.report_title.setObjectName("SectionTitle")
        self.report_hint = QtWidgets.QLabel(
            "Each row explains what happened. Green means the name is correct, amber means it needs a fix, and blue means it was skipped."
        )
        self.report_hint.setWordWrap(True)
        self.report_hint.setObjectName("SectionDescription")

        self.results_list = QtWidgets.QListWidget()
        self.results_list.setObjectName("ResultsList")
        self.results_list.setSpacing(6)
        report_layout.addWidget(self.report_title)
        report_layout.addWidget(self.report_hint)
        report_layout.addWidget(self.results_list, stretch=1)
        right_layout.addWidget(self.report_card, stretch=1)

        body_layout.addWidget(self.right_panel, stretch=2)
        main_layout.addWidget(self.body_panel, stretch=1)

        self.footer_label = QtWidgets.QLabel(
            "Tip: static mesh actors should start with SM_. This dialog is designed to be read at a glance."
        )
        self.footer_label.setObjectName("FooterLabel")
        self.footer_label.setWordWrap(True)
        main_layout.addWidget(self.footer_label)

    def _create_stat_card(self, title):
        card = QtWidgets.QFrame()
        card.setObjectName("StatCard")
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)

        value = QtWidgets.QLabel("0")
        value.setObjectName("StatValue")
        label = QtWidgets.QLabel(title)
        label.setObjectName("StatLabel")

        layout.addWidget(value)
        layout.addWidget(label)
        return card, value

    def _apply_styles(self):
        self.setStyleSheet(
            """
            #GatekeeperWindow {
                background: #151515;
                color: #ffffff;
            }
            #HeaderPanel {
                background: #2F2F2F;
                border: none;
                border-bottom: 1px solid #4a4a4a;
            }
            #BodyPanel {
                background: transparent;
            }
            #LeftPanel {
                background: #2F2F2F;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
            }
            #RightPanel {
                background: transparent;
            }
            #SummaryCard, #ActionsCard, #ReportCard {
                background: #2F2F2F;
                border: 1px solid #4a4a4a;
            }
            #SummaryCard {
                min-height: 96px;
            }
            #ActionsCard {
                border-color: transparent;
            }
            #ReportCard {
                min-height: 240px;
            }
            #TitleLabel {
                font-size: 21px;
                font-weight: 600;
                color: #ffffff;
            }
            #StatusPill {
                background: transparent;
                color: #ffffff;
                padding: 0px;
                font-weight: 500;
            }
            #SectionTitle {
                font-size: 15px;
                font-weight: 700;
                color: #ffffff;
            }
            #SectionDescription {
                color: #ffffff;
            }
            #HintLabel, #FooterLabel {
                color: #ffffff;
            }
            #SummaryText {
                color: #ffffff;
            }
            #StatCard {
                background: #2F2F2F;
                border: 1px solid #4a4a4a;
                border-radius: 0px;
                min-width: 128px;
            }
            #StatValue {
                font-size: 21px;
                font-weight: 700;
                color: #ffffff;
            }
            #StatLabel {
                color: #ffffff;
                font-size: 11px;
                text-transform: none;
                letter-spacing: 0px;
            }
            QPushButton {
                background: #2F2F2F;
                color: #ffffff;
                border: 2px solid #4a4a4a;
                padding: 10px 14px;
                border-radius: 0px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #383838;
            }
            QPushButton:pressed {
                background: #262626;
            }
            QPushButton#btnPrimary {
                background: #2F2F2F;
                border: 2px solid #3a74b8;
                font-weight: 600;
            }
            QPushButton#btnPrimary:hover {
                background: #383838;
            }
            #SelectionList,
            #ResultsList {
                background: #2F2F2F;
                border: 1px solid #4a4a4a;
                padding: 6px;
                color: #ffffff;
            }
            #ResultCard_pass {
                background: #2F2F2F;
                border: 2px solid #4a4a4a;
                border-left: 6px solid #2ea043;
                border-radius: 0px;
            }
            #ResultCard_warn {
                background: #2F2F2F;
                border: 2px solid #4a4a4a;
                border-left: 6px solid #d88a00;
                border-radius: 0px;
            }
            #ResultCard_info {
                background: #2F2F2F;
                border: 2px solid #4a4a4a;
                border-left: 6px solid #3f6fd6;
                border-radius: 0px;
            }
            #ResultTitle {
                font-size: 13px;
                font-weight: 600;
                color: #ffffff;
            }
            #ResultSubtitle {
                color: #ffffff;
            }
            """
        )
        self.btn_validate.setObjectName("btnPrimary")
        self.btn_validate.setMinimumHeight(40)
        self.btn_clear.setMinimumHeight(36)

    def _set_empty_state(self):
        self._summary = None
        self.total_value.setText("0")
        self.passed_value.setText("0")
        self.flagged_value.setText("0")
        self.summary_text.setText("0 actors selected\n0 StaticMesh actors validated\n0 items need attention")
        self.results_list.clear()
        self.selection_list.clear()
        self._add_result_item(
            "No selection yet",
            "Select actors in the Outliner and press Analyze selection.",
            "info",
        )

    def _start_live_selection_updates(self):
        self.selection_timer = QtCore.QTimer(self)
        self.selection_timer.setInterval(500)
        self.selection_timer.timeout.connect(self.refresh_live_selection)
        self.selection_timer.start()

    def _build_selection_signature(self, actors):
        return tuple(
            (
                getattr(actor, "get_actor_label", lambda: getattr(actor, "name", "Unknown Actor"))(),
                getattr(getattr(actor, "get_class", lambda: actor.__class__)(), "get_name", lambda: actor.__class__.__name__)(),
            )
            for actor in actors
        )

    def refresh_live_selection(self):
        actors = get_selected_level_actors()
        signature = self._build_selection_signature(actors)
        if signature == self._last_selection_signature:
            return

        self._last_selection_signature = signature
        live_summary = run_naming_validation(actors)
        self._update_live_preview(live_summary)

    def _update_live_preview(self, summary):
        self.total_value.setText(str(summary.total_selected))
        self.passed_value.setText(str(summary.passed))
        self.flagged_value.setText(str(summary.flagged))
        self.summary_text.setText(
            f"{summary.total_selected} actors selected\n"
            f"{summary.checked_static_meshes} StaticMesh actors in selection\n"
            f"{summary.flagged} items need attention"
        )
        self._sync_selection_snapshot(summary)

        if summary.total_selected == 0:
            self.status_label.setText("No actors are currently selected.")
        elif summary.flagged:
            self.status_label.setText("Some names need attention.")
        else:
            self.status_label.setText("Current selection looks good.")

        if self._summary is None:
            self.results_list.clear()
            self._add_result_item(
                "Live selection updated",
                "The left panel mirrors the current Outliner selection in real time.",
                "info",
            )

    def _sync_selection_snapshot(self, summary):
        self.selection_list.clear()
        if not summary.items:
            item = QtWidgets.QListWidgetItem("Nothing selected")
            self.selection_list.addItem(item)
            return

        for item in summary.items:
            if item.status == "pass":
                prefix = "PASS"
            elif item.status == "flag":
                prefix = "REVIEW"
            else:
                prefix = "SKIP"
            self.selection_list.addItem(f"{prefix} | {item.actor_label} | {item.actor_class}")

    def _add_result_item(self, title, subtitle, status):
        item = QtWidgets.QListWidgetItem()
        widget = QtWidgets.QFrame()
        widget.setObjectName(f"ResultCard_{status}")
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title_label = QtWidgets.QLabel(title)
        title_label.setObjectName("ResultTitle")
        subtitle_label = QtWidgets.QLabel(subtitle)
        subtitle_label.setWordWrap(True)
        subtitle_label.setObjectName("ResultSubtitle")

        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)

        item.setSizeHint(widget.sizeHint())
        self.results_list.addItem(item)
        self.results_list.setItemWidget(item, widget)

    def _render_summary(self, summary):
        self._summary = summary
        self.total_value.setText(str(summary.total_selected))
        self.passed_value.setText(str(summary.passed))
        self.flagged_value.setText(str(summary.flagged))
        self.summary_text.setText(
            f"{summary.total_selected} actors selected\n"
            f"{summary.checked_static_meshes} StaticMesh actors validated\n"
            f"{summary.flagged} items need attention"
        )
        self._sync_selection_snapshot(summary)

        if summary.total_selected == 0:
            self.status_label.setText("No actors are currently selected.")
        elif summary.flagged:
            self.status_label.setText("Some names need attention.")
        else:
            self.status_label.setText("Everything looks good.")

        self.results_list.clear()
        if not summary.items:
            self._add_result_item("No data", "No items were found to review.", "info")
            return

        for item in summary.items:
            if item.status == "pass":
                title = f"✅ {item.actor_label}"
                status = "pass"
            elif item.status == "flag":
                title = f"⚠ {item.actor_label}"
                status = "warn"
            else:
                title = f"ℹ {item.actor_label}"
                status = "info"
            subtitle = f"{item.actor_class} · {item.message}"
            self._add_result_item(title, subtitle, status)

    def run_naming_audit(self):
        summary = run_naming_validation(get_selected_level_actors())
        self._render_summary(summary)

    def clear_results(self):
        self._set_empty_state()


def spawn_window():
    if QtWidgets is None:
        print(
            "Gatekeeper UI no pudo iniciarse porque no se encontró PySide6 ni PySide2 en el Python de Unreal."
        )
        return

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    global gatekeeper_instance
    try:
        if "gatekeeper_instance" in globals() and gatekeeper_instance is not None:
            gatekeeper_instance.close()
            gatekeeper_instance.deleteLater()
    except Exception:
        pass

    gatekeeper_instance = GatekeeperWindow()
    if hasattr(unreal, "parent_external_window_to_slate"):
        unreal.parent_external_window_to_slate(gatekeeper_instance.winId())
    gatekeeper_instance.show()
    gatekeeper_instance.raise_()
    gatekeeper_instance.activateWindow()


if __name__ == "__main__":
    spawn_window()
