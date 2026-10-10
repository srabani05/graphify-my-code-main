"""Sample python service with a cross-module call."""
from billing.pricing import calc_total


class Cart:
    def __init__(self, items):
        self.items = items

    def checkout(self, user):
        total = calc_total(self.items)
        return {"user": user, "total": total}
