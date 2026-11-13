# Simulation bench

The hub can run without a family, an accelerator or a language model. The simulated path is a set of small HTTP stand-ins for the children of the family (a healthy
one, a sick one, one with the uniform route closed, a slow one, one that answers something that is not JSON and one that answers more than the limit), the real
probe of the hub that asks them, the simulated backend of the language model driven by facts drawn from a fixed seed, and backends that fail, hang or answer with
control characters in place of an accelerator that is lost or busy.

## Run it

```
PYTHONPATH=src python -m pytest -q tests/test_simulation_bench.py
```

## What the scenarios check

| Scenario | What it shows |
|----------|---------------|
| a family in every state | healthy, sick (503) and a status word are told apart; an answer without a verdict stands as up when the status is a success |
| children that are not there | each one is unreachable with its reason and the others are not hidden |
| the uniform route closed | the probe asks the second route and reads it |
| an oversized answer, a slow child | the answer is read only up to the limit; a child slower than the timeout is unreachable and the probe does not hang |
| the narrative in eight languages | every number in the text is one of the facts that were given, in every language |
| the same seed twice, another seed | the narratives are reproducible and really depend on the seed |
| a lost accelerator | the request fails closed and the slot is given back |
| a busy accelerator | the second request is refused, the first still finishes and the next one is served |
| control characters from a model, a model that says nothing | the text is cleaned before it leaves; an empty answer is "unavailable" and never an empty narrative |

The workflow named "Simulation bench" runs this file on every change, so the simulated path has its own visible job.

## What it cannot show

A real accelerator, a real language model, the latency of either and the behaviour of the real children of the family need the hardware and the models. The status
of the repository therefore stays at "simulated" for the hardware row until a person has run the hub on the bench.
