import asyncio
import pytest
from toolcrate.core.events import EventBus, Event


async def test_subscriber_receives_published_event():
    bus = EventBus()
    sub = bus.subscribe()
    await bus.publish(Event(name="job.update", data={"id": 1, "state": "running"}))
    received = await asyncio.wait_for(anext(sub), timeout=1)
    assert received.name == "job.update"
    assert received.data["state"] == "running"
    await bus.unsubscribe(sub)


async def test_two_subscribers_each_receive_event():
    bus = EventBus()
    a = bus.subscribe()
    b = bus.subscribe()
    await bus.publish(Event(name="x", data={}))
    ra = await asyncio.wait_for(anext(a), timeout=1)
    rb = await asyncio.wait_for(anext(b), timeout=1)
    assert ra.name == rb.name == "x"


async def test_unsubscribe_stops_delivery():
    bus = EventBus()
    sub = bus.subscribe()
    await bus.unsubscribe(sub)
    # should be a no-op; publishing now must not raise
    await bus.publish(Event(name="x", data={}))


async def test_topic_filtering():
    bus = EventBus()
    sub = bus.subscribe(topics={"jobs"})
    await bus.publish(Event(name="lists.updated", data={}, topic="lists"))
    await bus.publish(Event(name="job.update", data={}, topic="jobs"))
    ev = await asyncio.wait_for(anext(sub), timeout=1)
    assert ev.topic == "jobs"
