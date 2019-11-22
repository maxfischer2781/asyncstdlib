=================
Glossary of Terms
=================

.. Using references in the glossary itself:
   When mentioning other items, always reference them.
   When mentioning the current item, never reference it.


.. glossary::

    Async Neutral

    Colour Neutral
        Ongoing action that drives forward a simulation - either through :term:`time` or :term:`events <event>`.
        Activities may be :term:`suspended <Suspension>` and resumed as desired, or interrupted involuntarily.

    Time
        Representation of the progression of a simulation.
        Whereas the unit of time is arbitrary, its value always grows.

        Time may only pass while all :term:`activities <Activity>`
        are :term:`suspended <Suspension>` until a later time, not :term:`turn`.
        An :term:`activity` may actively wait for the progression of time,
        or implicitly delay until an event happens at a future point in time.

    Turn
        Inherent ordering of :term:`events <event>` happening at the same :term:`time`.

    Event
        A well-defined occurrence at a specific point in :term:`time`.
        Events may occur
        as result of activities ("when dinner is done"),
        as time passes ("after 20 time units"),
        or
        at predefined points in time ("at 2000 time units"),

    Notification
        Information sent to an :term:`activity`, usually in response to an :term:`event`.
        Notifications are only received when the :term:`activity`
        is :term:`suspended <Suspension>`, i.e. at an ``await``, ``async for`` or ``async with``.

    Postponement
        :term:`Suspension` of an :term:`activity` until a later :term:`turn` at the same :term:`time`.
        When an :term:`activity` is postponed, :term:`notifications <Notification>` may be received
        and other :term:`activities <Activity>` may run but :term:`time` does not advance.

        :note: μSim guarantees that all its primitives postpone on asynchronous operations.
               This ensures that activities are reliably and deterministically interwoven.

    Suspension
        Pause the execution of an :term:`activity`,
        allowing other :term:`activities <activity>` or :term:`time` to advance.
        A suspended activity is only resumed when it receives a :term:`notification`.

        Suspension can only occur as part of asynchronous statements:
        waiting for the target of an ``await`` statement,
        fetching the next item of an ``async for`` statement,
        and entering/exiting an ``async with`` block.
