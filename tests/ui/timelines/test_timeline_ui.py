from unittest.mock import patch

import pytest

from tests.mock import Serve
from tests.ui.timelines.interact import (
    click_timeline_ui,
    click_timeline_ui_element_body,
)
from tests.utils import undoable
from tilia.requests import Get, Post, post
from tilia.settings import settings
from tilia.timelines.component_kinds import ComponentKind
from tilia.timelines.marker.timeline import MarkerTimeline
from tilia.ui import commands
from tilia.ui.timelines.base.timeline import TimelineUI
from tilia.ui.timelines.collection.collection import TimelineSelector


def get_time_shifted_args(args: dict[str, int], d_time) -> dict[str, int]:
    if "time" in args:
        args["time"] += d_time
    else:
        args["start"] += d_time
        args["end"] += d_time
    return args


@pytest.mark.parametrize(
    "tlui, args",
    [
        (
            "audiowave_tlui",
            {"kind": ComponentKind.AUDIOWAVE, "start": 50, "end": 55, "amplitude": 10},
        ),
        ("beat_tlui", {"kind": ComponentKind.BEAT, "time": 50}),
        ("harmony_tlui", {"kind": ComponentKind.HARMONY, "time": 50}),
        ("harmony_tlui", {"kind": ComponentKind.MODE, "time": 50}),
        (
            "hierarchy_tlui",
            {"kind": ComponentKind.HIERARCHY, "start": 50, "end": 55, "level": 2},
        ),
        ("marker_tlui", {"kind": ComponentKind.MARKER, "time": 50}),
        ("pdf_tlui", {"kind": ComponentKind.PDF_MARKER, "time": 50, "page_number": 1}),
        # "score_tlui", setup is a little too complicated
        # "slider_tlui", not clickable
    ],
)
class TestModifierSelect:
    @pytest.mark.parametrize(
        "modifiers,changes_time,select_value",
        [
            (["alt", "ctrl"], False, [True, False]),
            (["alt"], False, [True, True]),
            (["ctrl"], True, [True, False]),
        ],
        ids=["alt+ctrl", "alt", "ctrl"],
    )
    def test_single(
        self,
        qtui,
        tlui,
        args,
        tilia_state,
        request,
        modifiers,
        changes_time,
        select_value,
    ):
        tlui = request.getfixturevalue(tlui)
        tlui.create_component(**args)

        if "time" in args:
            click_time = tlui[0].get_data("time")
        else:
            click_time = tlui[0].get_data("start")

        for i in range(10):
            click_timeline_ui_element_body(tlui[0], modifier=modifiers)
            assert tlui[0].is_selected() == select_value[i % 2]
            assert tilia_state.current_time == (click_time if changes_time else 0)

    @pytest.mark.parametrize(
        "modifiers,changes_time,select_value",
        [
            (
                ["alt", "ctrl"],
                False,
                [(True, False), (True, True), (False, True), (False, False)],
            ),
            (
                ["alt"],
                False,
                [(True, False), (False, True), (True, False), (False, True)],
            ),
            (
                [
                    "ctrl",
                    True,
                    [(True, False), (True, True), (False, True), (False, False)],
                ]
            ),
        ],
        ids=["alt+ctrl", "alt", "ctrl"],
    )
    def test_multiple(
        self,
        qtui,
        tlui,
        args,
        tilia_state,
        request,
        modifiers,
        changes_time,
        select_value,
    ):
        tlui = request.getfixturevalue(tlui)
        tlui.create_component(**args)
        tlui.create_component(**get_time_shifted_args(args, 10))

        if "time" in args:
            click_time = [tlui[0].get_data("time"), tlui[1].get_data("time")]
        else:
            click_time = [tlui[0].get_data("start"), tlui[1].get_data("start")]

        click_timeline_ui_element_body(tlui[0], modifier=modifiers)
        assert ((tlui[0].is_selected(), tlui[1].is_selected())) == select_value[0]
        assert tilia_state.current_time == (click_time[0] if changes_time else 0)

        click_timeline_ui_element_body(tlui[1], modifier=modifiers)
        assert (tlui[0].is_selected(), tlui[1].is_selected()) == select_value[1]
        assert tilia_state.current_time == (click_time[1] if changes_time else 0)

        click_timeline_ui_element_body(tlui[0], modifier=modifiers)
        assert (tlui[0].is_selected(), tlui[1].is_selected()) == select_value[2]
        assert tilia_state.current_time == (click_time[0] if changes_time else 0)

        click_timeline_ui_element_body(tlui[1], modifier=modifiers)
        assert (tlui[0].is_selected(), tlui[1].is_selected()) == select_value[3]
        assert tilia_state.current_time == (click_time[1] if changes_time else 0)


class TestControlSelect:
    def test_does_not_deselect_if_nothing_clicked(self, marker_tlui):
        marker_tlui.create_marker(0)

        click_timeline_ui(marker_tlui, 0, modifier="ctrl")
        click_timeline_ui(marker_tlui, 50, modifier="ctrl")
        assert marker_tlui[0].is_selected()


@pytest.mark.parametrize(
    "tlui,component_kind",
    [
        ("harmony", ComponentKind.HARMONY),
        ("harmony", ComponentKind.MODE),
        ("marker", ComponentKind.MARKER),
        ("beat", ComponentKind.BEAT),
        # ("hierarchy", ComponentKind.HIERARCHY),
        # ("audiowave",ComponentKind.AUDIOWAVE)
    ],
    indirect=["tlui"],
)
class TestArrowSelection:
    def test_clicking_right_arrow_selects_next_element(self, tlui, component_kind):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.select_element(tlui[0])

        post(Post.TIMELINE_KEY_PRESS_RIGHT)

        assert not tlui[0].is_selected()
        assert tlui[1].is_selected()

    def test_clicking_right_arrow_with_multiple_selected_selects_next_element(
        self, tlui, component_kind
    ):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.create_component(component_kind, 20)
        tlui.create_component(component_kind, 30)
        tlui.select_element(tlui[0])
        tlui.select_element(tlui[1])
        tlui.select_element(tlui[2])

        post(Post.TIMELINE_KEY_PRESS_RIGHT)

        assert not tlui[0].is_selected()
        assert not tlui[1].is_selected()
        assert not tlui[2].is_selected()
        assert tlui[3].is_selected()

    def test_clicking_right_arrow_does_nothing_if_last_element_is_selected(
        self, tlui, component_kind
    ):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.select_element(tlui[1])

        post(Post.TIMELINE_KEY_PRESS_RIGHT)

        assert not tlui[0].is_selected()
        assert tlui[1].is_selected()

    def test_clicking_left_arrow_selects_previous_element(self, tlui, component_kind):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.select_element(tlui[1])

        post(Post.TIMELINE_KEY_PRESS_LEFT)

        assert tlui[0].is_selected()
        assert not tlui[1].is_selected()

    def test_clicking_left_arrow_with_multiple_selected_selects_previous_element(
        self, tlui, component_kind
    ):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.create_component(component_kind, 20)
        tlui.create_component(component_kind, 30)
        tlui.select_element(tlui[1])
        tlui.select_element(tlui[2])
        tlui.select_element(tlui[3])

        post(Post.TIMELINE_KEY_PRESS_LEFT)

        assert tlui[0].is_selected()
        assert not tlui[1].is_selected()
        assert not tlui[2].is_selected()
        assert not tlui[3].is_selected()

    def test_clicking_left_arrow_does_nothing_if_first_element_is_selected(
        self, tlui, component_kind
    ):
        tlui.create_component(component_kind, 0)
        tlui.create_component(component_kind, 10)
        tlui.select_element(tlui[0])

        post(Post.TIMELINE_KEY_PRESS_LEFT)

        assert tlui[0].is_selected()
        assert not tlui[1].is_selected()


class TestSetTimelineName:
    def test_set(self, tls, tluis):
        tls.create_timeline(MarkerTimeline, name="change me")
        with Serve(Get.FROM_USER_STRING, (True, "this")):
            commands.execute("timeline.set_name", tluis[0])

        assert tls[0].get_data("name") == "this"
        assert tluis[0].displayed_name == "this"

    def test_set_undo(self, tls, tluis):
        commands.execute("timelines.add.marker", name="pure")
        commands.execute("timeline.set_name", tluis[0], name="tainted")

        commands.execute("edit.undo")

        assert tls[0].get_data("name") == "pure"
        assert tluis[0].displayed_name == "pure"

    def test_set_redo(self, tls, tluis):
        commands.execute("timelines.add.marker", name="pure")
        commands.execute("timeline.set_name", tluis[0], name="tainted")

        commands.execute("edit.undo")
        commands.execute("edit.redo")

        assert tls[0].get_data("name") == "tainted"
        assert tluis[0].displayed_name == "tainted"

    def test_set_empty_string(self, tls, tluis):
        tls.create_timeline(MarkerTimeline, name="change me")
        # name="" can't skip the prompt: on_timeline_set_name checks `if not name`.
        with Serve(Get.FROM_USER_STRING, (True, "")):
            commands.execute("timeline.set_name", tluis[0])

        assert tls[0].get_data("name") == ""
        assert tluis[0].displayed_name == ""


def test_set_is_visible(tls, marker_tlui):
    with undoable():
        commands.execute("timeline.set_is_visible", marker_tlui, False)

    assert not marker_tlui.view.isVisible()

    with undoable():
        commands.execute("timeline.set_is_visible", marker_tlui, True)

    assert marker_tlui.view.isVisible()


class TestOnTimelineCommand:
    @staticmethod
    def call_on_timeline_command(tluis, callback):
        tluis.on_timeline_command([MarkerTimeline], callback, TimelineSelector.ALL)

    @staticmethod
    def add_timeline(count=1):
        for _ in range(count):
            commands.execute("timelines.add.marker", name="")

    def test_command_callback_error_is_displayed_if_callback_is_function(
        self, tls, tluis, tilia_errors
    ):
        def fail(*args, **kwargs):
            raise ValueError

        self.add_timeline()
        self.call_on_timeline_command(tluis, fail)

        tilia_errors.assert_error()
        tilia_errors.assert_in_error_message(fail.__name__)

    def test_command_callback_error_is_displayed_if_callback_is_method(
        self, tls, tluis, tilia_errors
    ):
        class Dummy:
            def fail(self, *args, **kwargs):
                raise ValueError

        dummy = Dummy()
        self.add_timeline()
        self.call_on_timeline_command(tluis, dummy.fail)

        tilia_errors.assert_error()
        tilia_errors.assert_in_error_message(dummy.fail.__name__)

    def test_command_callback_error_is_displayed_if_callback_is_something_else(
        self, tls, tluis, tilia_errors
    ):
        self.add_timeline()
        self.call_on_timeline_command(tluis, "not a function")

        tilia_errors.assert_error()
        tilia_errors.assert_in_error_message("not a function")

    def test_command_callback_return_invalid_value_single_timeline(
        self, tluis, tilia_errors
    ):
        self.add_timeline()

        def return_invalid_value(*args, **kwargs):
            return "not a boolean"

        self.call_on_timeline_command(tluis, return_invalid_value)

        tilia_errors.assert_error()
        tilia_errors.assert_in_error_message("not a boolean")

    def test_command_callback_return_invalid_value_multiple_timelines(
        self, tluis, tilia_errors
    ):
        self.add_timeline(count=3)

        def value_generator():
            yield True
            yield True
            yield "not a boolean"

        gen = value_generator()

        self.call_on_timeline_command(tluis, lambda *args, **kwargs: next(gen))

        tilia_errors.assert_error()

    @pytest.mark.parametrize("return_value", [True, False])
    def test_command_callback_return_valid_value_single_timeline(
        self, return_value, tluis, tilia_errors
    ):
        self.add_timeline()

        self.call_on_timeline_command(tluis, lambda *args, **kwargs: return_value)

        tilia_errors.assert_no_error()

    @pytest.mark.parametrize(
        "return_values",
        (
            [True, True, True],
            [True, True, False],
            [True, False, True],
            [False, True, True],
            [False, False, False],
        ),
    )
    def test_command_callback_return_valid_value_list(
        self, return_values, tluis, tilia_errors
    ):
        self.add_timeline(count=3)

        def value_generator():
            yield return_values[0]
            yield return_values[1]
            yield return_values[2]

        gen = value_generator()
        self.call_on_timeline_command(tluis, lambda *args, **kwargs: next(gen))

        tilia_errors.assert_no_error()


def test_ensure_timeline_ui_subclasses_is_only_called_once():
    # Subclasses were already loaded in previous tests, so we reset the flag
    TimelineUI.SUBCLASSES_ARE_LOADED = False
    with patch.object(
        TimelineUI,
        "ensure_subclasses_are_available",
        wraps=TimelineUI.ensure_subclasses_are_available,
    ) as wrapped:
        for _ in range(50):
            TimelineUI.subclasses()
        assert wrapped.call_count == 1


@pytest.mark.parametrize(
    "tlui, group, add_element",
    [
        (
            "hierarchy_tlui",
            "hierarchy_timeline",
            lambda: commands.execute(
                "timeline.hierarchy.add", start=0, end=50, level=1
            ),
        ),
        (
            "range_tlui",
            "range_timeline",
            lambda: commands.execute("timeline.range.add_range", start=0, end=50),
        ),
        ("beat_tlui", "beat_timeline", lambda: commands.execute("timeline.beat.add")),
    ],
)
class TestLabelFont:
    @staticmethod
    def set_font(group, size, bold, italic, underline):
        settings.set(group, "label_font_size", size)
        settings.set(group, "label_bold", bold)
        settings.set(group, "label_italic", italic)
        settings.set(group, "label_underline", underline)

    @staticmethod
    def assert_font(element, size, bold, italic, underline):
        font = element.label.font()
        assert font.pointSize() == size
        assert font.bold() == bold
        assert font.italic() == italic
        assert font.underline() == underline

    def test_settings_change_restyles_labels(self, tlui, group, add_element, request):
        tlui = request.getfixturevalue(tlui)
        add_element()

        self.set_font(group, 18, True, True, True)
        post(Post.SETTINGS_UPDATED, [group])

        self.assert_font(tlui[0], 18, True, True, True)

    def test_new_labels_use_settings(self, qtui, tlui, group, add_element, request):
        tlui = request.getfixturevalue(tlui)
        self.set_font(group, 6, False, True, False)

        add_element()

        self.assert_font(tlui[0], 6, False, True, False)

    def test_other_kinds_settings_dont_apply(self, tlui, group, add_element, request):
        tlui = request.getfixturevalue(tlui)
        self.set_font(group, 10, False, False, False)
        add_element()
        other_group = "marker_timeline"
        self.set_font(other_group, 20, True, True, True)

        post(Post.SETTINGS_UPDATED, [other_group, group])

        self.assert_font(tlui[0], 10, False, False, False)


class TestMarkerLabelFont:
    def test_settings_change_restyles_labels(self, marker_tlui):
        commands.execute("timeline.marker.add")

        TestLabelFont.set_font("marker_timeline", 18, True, False, True)
        post(Post.SETTINGS_UPDATED, ["marker_timeline"])

        TestLabelFont.assert_font(marker_tlui[0], 18, True, False, True)

    def test_label_stays_centred_on_marker(self, marker_tlui):
        commands.execute("timeline.marker.add")

        TestLabelFont.set_font("marker_timeline", 30, False, False, False)
        post(Post.SETTINGS_UPDATED, ["marker_timeline"])

        label = marker_tlui[0].label
        assert label.x() + label.boundingRect().width() / 2 == pytest.approx(
            marker_tlui[0].x
        )


class TestHierarchyLabelFont:
    def test_larger_font_crops_label_more(self, hierarchy_tlui):
        commands.execute(
            "timeline.hierarchy.add", start=0, end=1, level=1, label="a long label"
        )
        settings.set("hierarchy_timeline", "label_font_size", 10)
        post(Post.SETTINGS_UPDATED, ["hierarchy_timeline"])
        cropped_small = hierarchy_tlui[0].label.toPlainText()

        settings.set("hierarchy_timeline", "label_font_size", 20)
        post(Post.SETTINGS_UPDATED, ["hierarchy_timeline"])

        assert len(hierarchy_tlui[0].label.toPlainText()) < len(cropped_small)

    def test_label_is_centred_in_its_level(self, hierarchy_tlui):
        commands.execute(
            "timeline.hierarchy.add", start=0, end=50, level=2, label="label"
        )
        settings.set("hierarchy_timeline", "label_font_size", 8)
        post(Post.SETTINGS_UPDATED, ["hierarchy_timeline"])

        element = hierarchy_tlui[0]
        label = element.label
        level_top = element.body.rect().top()
        level_height = settings.get("hierarchy_timeline", "level_height_diff")
        label_centre = label.y() + label.boundingRect().height() / 2
        assert label_centre == pytest.approx(level_top + level_height / 2)


class TestTimelineNameFont:
    def test_settings_change_restyles_name(self, marker_tlui):
        settings.set("general", "timeline_name_font_size", 16)
        settings.set("general", "timeline_name_bold", True)
        settings.set("general", "timeline_name_italic", True)
        settings.set("general", "timeline_name_underline", True)

        post(Post.SETTINGS_UPDATED, ["general"])

        font = marker_tlui.scene.text.font()
        assert font.pointSize() == 16
        assert font.bold()
        assert font.italic()
        assert font.underline()

    def test_new_timeline_uses_settings(self, tluis):
        settings.set("general", "timeline_name_font_size", 14)
        settings.set("general", "timeline_name_italic", True)

        commands.execute("timelines.add.marker", name="name")

        font = tluis[0].scene.text.font()
        assert font.pointSize() == 14
        assert font.italic()
