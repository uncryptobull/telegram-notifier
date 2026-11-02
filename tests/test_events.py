from telegram_notifier.events import Gate


def test_online_refresh_does_not_repeat_alert():
    now = [100]
    gate = Gate(lambda: now[0])
    assert gate.status(True, 200)
    now[0] = 130
    assert not gate.status(True, 250)
    gate.status(False)
    assert gate.status(True, 300)


def test_initial_baseline_and_expired_online_status():
    now = [100]
    gate = Gate(lambda: now[0])
    assert not gate.status(True, 110, enabled=False)
    now[0] = 130
    assert gate.status(True, 200)


def test_independent_event_cooldowns():
    now = [100]
    gate = Gate(lambda: now[0], cooldown=30)
    assert gate.status(True, 200)
    assert gate.typing(True)
    now[0] = 120
    gate.status(False)
    assert not gate.status(True, 200)
    assert not gate.typing(True)
    now[0] = 160
    assert gate.typing(True)


def test_continuous_typing_is_one_burst():
    now = [100]
    gate = Gate(lambda: now[0])
    assert gate.typing(True)
    for second in range(101, 145):
        now[0] = second
        assert not gate.typing(True)
    gate.typing(False)
    assert gate.typing(True)


def test_disabled_event_still_updates_baseline():
    gate = Gate(lambda: 100)
    assert not gate.status(True, 200, enabled=False)
    assert not gate.status(True, 200, enabled=True)
    assert not gate.typing(True, enabled=False)
    assert not gate.typing(True, enabled=True)
