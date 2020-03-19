from asyncstdlib import _utility


def test_slot_get():
    class Slotted:
        data = 3

        def __neg__(self):
            return -type(self).data

    instance = Slotted()
    assert _utility.slot_get(instance, "data") is instance.data
    assert _utility.slot_get(instance, "__neg__")() == -instance
    assert _utility.slot_get(instance, "__neg__")() == instance.__neg__()
    data, neg = instance.data, -instance
    instance.data = 4
    instance.__neg__ = lambda self: 12
    assert _utility.slot_get(instance, "data") is data
    assert _utility.slot_get(instance, "__neg__")() == neg
