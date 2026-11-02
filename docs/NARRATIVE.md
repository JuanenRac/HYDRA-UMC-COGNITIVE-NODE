# POST /narrative - the local language model

Off by default. Without `--llm-config FILE` (or `HYDRA_UMC_COGNITIVE_NODE_LLM_CONFIG`), or with `"enabled": false` in it, the route does not exist (`404`).

A client (the dashboard of AI summaries) sends the **numbers** of a trend summary and the node writes a short sentence about them. The node never takes free
text: the prompt is built here, from the facts, and an unknown field, an identifier with anything but letters, digits and `_ - . :`, a number that is not
finite or a body over 8 KiB is a `400`. The text that comes back is cleaned (control characters and bidirectional overrides removed, at most 2000
characters). Whether the numbers in the text are the numbers that were sent is checked by the caller before it shows anything.

## Request

`POST /narrative` with the bearer token when the node has one:

```json
{"sourceId": "motor-1", "kind": "vibration", "field": "rms", "count": 120, "min": 0.5, "max": 3.25, "average": 1.8, "latest": 2.75,
 "direction": "up", "language": "es"}
```

`direction` is `up`, `down` or `flat`; `language` is one of `en es de fr it ja zh pt` (default `en`; `pt` is European Portuguese).

## Answer

`200 {"narrative": "...", "backend": "simulator", "model": "simulator-faithful", "language": "es"}`. `400` for a request that is not facts, `401` without the
token, `503` when the accelerator is not available (no runtime, no model file, a failure of the device) or when `maxConcurrent` narratives are already being
made (`Retry-After: 2`).

## Configuration file

```json
{
  "enabled": true,
  "backend": "simulator",
  "modelPath": null,
  "maxTokens": 160,
  "maxConcurrent": 1,
  "simulator": {"variant": "faithful"}
}
```

* `backend` is `simulator` (default) or `hailo`. `hailo` needs `modelPath`, the compiled model file for the Hailo-10, and HailoRT with GenAI on the machine.
* `maxTokens` 16 to 1024 (default 160); `maxConcurrent` 1 to 16 (default 1, the accelerator answers one request at a time).
* `simulator.variant`: `faithful` (the numbers it was given), `altered` (changes the latest value, to prove that the caller's check rejects it) or
  `silent` (a sentence with no numbers). The simulator answers in the eight languages from a template; it is not a model and the node says so when it starts.
* A misspelt key stops the start with a message.

## What has and has not been tried

Everything above runs and is tested with the simulator. The `hailo` backend is written against the documented HailoRT GenAI interface but **has never run on
a Hailo-10**: any failure is reported as `503`, never guessed. Its first run on real hardware is pending.
