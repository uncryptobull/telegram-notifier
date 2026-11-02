import time


class Gate:
    def __init__(self, clock=time.monotonic, cooldown=15):
        self.clock = clock
        self.cooldown = cooldown
        self.online = None
        self.expires = 0
        self.last_online_alert = float("-inf")
        self.last_typing = float("-inf")
        self.last_typing_alert = float("-inf")

    def status(self, online, expires=0, enabled=True):
        now = self.clock()
        was_online = self.online is True and now < self.expires
        self.online = online
        self.expires = expires
        if online and not was_online and enabled and now - self.last_online_alert >= self.cooldown:
            self.last_online_alert = now
            return True
        return False

    def typing(self, active, enabled=True):
        now = self.clock()
        if not active:
            self.last_typing = float("-inf")
            return False
        new_burst = now - self.last_typing > 6
        self.last_typing = now
        if new_burst and enabled and now - self.last_typing_alert >= self.cooldown:
            self.last_typing_alert = now
            return True
        return False
