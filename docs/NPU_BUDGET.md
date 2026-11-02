# The budget of the accelerator

Off by default. Without `--npu-config FILE` (or `HYDRA_UMC_COGNITIVE_NODE_NPU_CONFIG`), or with `"enabled": false` in it, the routes below do not exist (`404`) and the language model of `POST /narrative` works as before.

The Hailo-10 is one device and three kinds of work want it: the VLA engine, the speech-to-text and the language model. This module decides who may use it; **it does not open the device**. A service asks for a lease before it opens the accelerator and gives it back when it is done.

* A lease has a deadline (`maxHoldSeconds` of its consumer), so a service that dies cannot keep the device. A lease that is not given back expires.
* When the device is busy the requests wait in a queue ordered by the priority of the consumer (higher first), then first come, first served. A request waits at most `maxWaitSeconds` of its consumer (the caller can ask for less, never more); past it the answer is busy, never a wait without end.
* A consumer can be limited to `maxConcurrent` leases at the same time; one that is at its limit does not block the others.

## Routes

* `POST /npu/acquire` with `{"consumer": "vla", "waitSeconds": 1}` answers `{"lease": "<id>"}`, `503` with `Retry-After: 1` when the device did not become free in time, `400` for an unknown consumer.
* `POST /npu/release` with `{"lease": "<id>"}` answers `{"released": true|false}`.
* `GET /npu` shows the slots, the leases held, the requests waiting and, per consumer, the leases granted and the requests that found the device busy.

They need the bearer token when the node has one. With the budget on, the language model of this node takes a lease of the consumer `llm` around each narrative, and a busy device is a `503` with `Retry-After`.

## Configuration file

```json
{
  "enabled": true,
  "slots": 1,
  "consumers": {
    "vla": {"priority": 3, "maxWaitSeconds": 2, "maxHoldSeconds": 10, "maxConcurrent": 1},
    "stt": {"priority": 2, "maxWaitSeconds": 5, "maxHoldSeconds": 30, "maxConcurrent": 1},
    "llm": {"priority": 1, "maxWaitSeconds": 5, "maxHoldSeconds": 60, "maxConcurrent": 1}
  }
}
```

`slots` is how many leases may be held at once (1 to 8); the three consumers above are the default when `consumers` is left out. A node that serves `POST /narrative` with the budget on needs a consumer called `llm`. A misspelt key stops the start with a message.

## What has and has not been tried

Everything runs and is tested with threads that stand in for the services. There was no Hailo-10, so what the real device does when two services open it, and whether a single process that owns `/dev/hailo0` and takes the requests (instead of leases) is the better design, is pending hardware. The VLA engine and the speech-to-text do not ask for leases yet.
