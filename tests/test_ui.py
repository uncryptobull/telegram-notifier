from unittest.mock import Mock, patch

from telegram_notifier.settings import Settings
from telegram_notifier.ui import Application


def test_demo_opens_without_loading_or_saving_real_profile():
    store = Mock()
    app = Application(store, demo=True, tray=False)
    app.update()
    assert len(app.tabs.tabs()) == 3
    assert app.target.get() == "Alex Morgan"
    assert app.start_button.winfo_ismapped()
    assert app.log.winfo_height() > 60
    app.save_preferences()
    store.read.assert_not_called()
    store.write.assert_not_called()
    app.emit("setup_complete")
    app.emit("finished")
    app._drain()
    assert app.status.get() == "Ready to monitor"
    assert "Monitoring stopped" not in app.contact_status.get()
    app.destroy()


def test_tray_close_does_not_stop_service():
    store = Mock()
    store.read.return_value = Settings()
    app = Application(store, tray=False)
    app.tray = Mock(visible=True)
    with patch.object(app, "withdraw") as hide, patch.object(app, "stop") as stop:
        app.close_window()
    hide.assert_called_once()
    stop.assert_not_called()
    app.destroy()


def test_exit_stops_service_and_tray():
    store = Mock()
    store.read.return_value = Settings()
    app = Application(store, tray=False)
    app.service = Mock()
    app.service.is_alive.return_value = True
    app.tray = Mock()
    app.exit()
    assert app.exiting
    app.service.stop.assert_called_once()
    app.tray.stop.assert_called_once()
    app.destroy()
