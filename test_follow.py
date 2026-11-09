import unittest
from unittest.mock import patch
import threading
import tempfile
from pathlib import Path
from follow import WatchState, frame, reply_matches, watch


class WatchTests(unittest.TestCase):
    def test_pause_skips_hardware_and_reports_pause(self):
        stop = threading.Event()
        paused = threading.Event()
        paused.set()
        reports = []
        with patch("follow.inventory") as inventory, \
                patch("follow.time.sleep", side_effect=lambda _: stop.set()):
            watch(1, False, stop_event=stop, pause_event=paused,
                  on_status=lambda kind, message: reports.append(kind))
        inventory.assert_not_called()
        self.assertEqual(reports, ["paused"])

    def test_stop_does_not_access_hardware(self):
        stop = threading.Event()
        stop.set()
        with patch("follow.inventory") as inventory:
            watch(1, False, stop_event=stop)
        inventory.assert_not_called()

    def test_watcher_waits_for_missing_devices_then_checks_mouse(self):
        with patch("follow.inventory", side_effect=[(False, None), (True, {"path": b"test"}),
                                                    KeyboardInterrupt]), \
                patch("follow.time.sleep"), patch("follow.Mouse") as mouse:
            mouse.return_value.info.return_value = (10, {"current_channel": 2, "host_count": 3})
            with self.assertLogs("mouse-follow", level="INFO") as logs:
                with self.assertRaises(KeyboardInterrupt):
                    watch(1, False)
            self.assertTrue(any("Waiting for BOTH" in line for line in logs.output))
            mouse.assert_called_once()
            mouse.return_value.close.assert_called_once()
            mouse.return_value.switch.assert_not_called()

    def test_permission_failure_keeps_watcher_alive(self):
        with patch("follow.inventory", side_effect=[(True, {"path": b"test"}),
                                                    KeyboardInterrupt]) as inventory, \
                patch("follow.time.sleep"), \
                patch("follow.Mouse", side_effect=RuntimeError("Permission denied")):
            with self.assertLogs("mouse-follow", level="ERROR"):
                with self.assertRaises(KeyboardInterrupt):
                    watch(1, False)
            self.assertEqual(inventory.call_count, 2)

    def armed(self):
        state = WatchState()
        for n in range(7):
            self.assertFalse(state.update(n / 2, True, True))
        self.assertTrue(state.armed)
        return state

    def test_departure_triggers_only_once(self):
        state = self.armed()
        self.assertFalse(state.update(3.5, False, True))
        self.assertFalse(state.update(5, False, True))
        self.assertTrue(state.update(5.5, False, True))
        self.assertFalse(state.update(6, False, True))

    def test_watcher_uses_the_mouse_found_at_departure(self):
        mouse_info = {"path": b"test"}
        state = unittest.mock.MagicMock(seen_since=0, armed=False)
        state.update.return_value = True
        with patch("follow.WatchState", return_value=state), \
                patch("follow.inventory", side_effect=[(True, mouse_info), (False, None)]), \
                patch("follow.switch_once") as switch, \
                patch("follow.time.sleep", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                watch(2, False)
        switch.assert_called_once_with(2, mouse_info)

    def test_starting_absent_never_triggers(self):
        state = WatchState()
        for n in range(20):
            self.assertFalse(state.update(n, False, True))

    def test_short_dropout_does_not_trigger(self):
        state = self.armed()
        self.assertFalse(state.update(3.5, False, True))
        self.assertFalse(state.update(4.5, True, True))
        self.assertFalse(state.update(5, False, True))
        self.assertFalse(state.update(6, False, True))

    def test_sleep_requires_fresh_baseline(self):
        state = self.armed()
        self.assertFalse(state.update(100, False, True))
        self.assertFalse(state.armed)

    def test_mouse_leaving_disarms(self):
        state = self.armed()
        self.assertFalse(state.update(4, False, False))
        self.assertFalse(state.update(5, False, True))
        self.assertFalse(state.update(8, False, True))

    def test_protocol_filters_unrelated_and_error_replies(self):
        self.assertEqual(len(frame(7, 1, [0])), 20)
        self.assertEqual(frame(7, 1, [0])[:5], bytes([17, 255, 7, 29, 0]))
        self.assertTrue(reply_matches([17, 255, 0, 13, 7, 0, 0], 0, 0))
        self.assertFalse(reply_matches([17, 255, 0, 14, 7, 0, 0], 0, 0))
        self.assertFalse(reply_matches([17, 255, 0], 0, 0))
        with self.assertRaises(RuntimeError):
            reply_matches([17, 255, 255, 0, 13, 2, 0], 0, 0)


class MacMappingTests(unittest.TestCase):
    def test_mapping_validation_and_persistence(self):
        from mac_menubar import load_mapping, save_mapping, validate_mapping
        self.assertEqual(validate_mapping({}), {"mouse_destination_channel": 1})
        self.assertEqual(validate_mapping({"mouse_destination_channel": "3"}),
                         {"mouse_destination_channel": 3})
        with self.assertRaises(ValueError):
            validate_mapping({"mouse_destination_channel": 4})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            save_mapping({"mouse_destination_channel": 2}, path)
            self.assertEqual(load_mapping(path), {"mouse_destination_channel": 2})


class TranslationTests(unittest.TestCase):
    def test_english_status_is_available(self):
        from i18n import status
        with patch.dict("os.environ", {"LANG": "en_US.UTF-8"}, clear=False):
            self.assertEqual(status("armed", destination_channel=1),
                             "Ready: mouse will switch to channel 1")

    def test_chinese_status_is_available(self):
        from i18n import status
        with patch.dict("os.environ", {"LANG": "zh_CN.UTF-8"}, clear=False):
            self.assertIn("监听就绪", status("armed", destination_channel=1))


if __name__ == "__main__":
    unittest.main()
