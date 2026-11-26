# The autonomy policy

Off by default. Without `--autonomy-config FILE` (or `HYDRA_UMC_COGNITIVE_NODE_AUTONOMY_CONFIG`), or with `"enabled": false` in it, the routes below do not exist (`404`).

The node is the one place that says how far an output of the AI services may go before it can move hardware. A proposal of the VLA engine, an intent of the voice interface or a plan of the semantic planner asks for a level; the policy answers with the level it grants to that source and a decision.

| Level | Meaning |
| --- | --- |
| `inform` | the output may be shown, never acted upon |
| `propose` | the output may become a proposal that a person reviews |
| `execute_with_confirmation` | the output may be executed, but only after a person confirmed that very action |

## Decision

* A source gets at most the level written for it in `sources`. A source that is not listed gets `defaultLevel`, `inform` unless the file says otherwise, so a new service can never move hardware before somebody wrote it down.
* A source can also have a credential of its own: write it as `"vla-engine": {"level": "propose", "tokenFile": "/path/to/token"}` (the short form, just the level, stays valid). A request that names that source is answered `deny` with the reason `source_credential` unless its bearer token is the one in that file, so a caller that holds only the token of the node cannot speak in the name of another service. The token needs at least 16 characters, the policy does not start when the file cannot be read, and `GET /autonomy/policy` lists the names that have a credential, never the tokens or the paths. Without `tokenFile` nothing changes.
* A request above the granted level is `deny`. A request for `execute_with_confirmation` within the granted level is `needs_confirmation` until the request carries `"humanConfirmed": true`, and then `allow`.
* The node does not see the person: `humanConfirmed` is what the caller says. The routes need the bearer token whenever the node has one, and the node refuses to start the policy on an address that is not loopback without a token. Who may call the route is the decision of the operator.

## Routes

* `POST /autonomy/evaluate` with `{"source": "vla-engine", "kind": "proposal", "actionId": "move-1", "level": "propose", "humanConfirmed": false, "language": "es"}` answers `{"decision": "allow|deny|needs_confirmation", "reason": "...", "message": "...", "requestedLevel": "...", "grantedLevel": "...", "language": "es", "auditHash": "..."}`. The message is in one of the eight languages (`en es de fr it ja zh pt`; `pt` is European Portuguese). `400` for a request that is not well formed.
* `GET /autonomy/policy` shows the levels and the sources. `GET /autonomy/audit?limit=N` (1 to 500, 50 by default) shows the newest decisions kept in memory.
* When the audit log cannot be written the answer is `503` and **no decision is given**: a caller must treat it as a refusal.

## Audit log

Every decision is appended to `auditFile` as one JSON line with the source, the kind, the action identifier, the requested and the granted level, the confirmation flag, the decision and the reason: never the content of a proposal. Each line holds the SHA-256 of the previous one, so a line that is removed or edited breaks the chain (`verify_chain` in `autonomy.py` checks a list of lines). When the file passes `auditMaxBytes` it becomes `<name>.1` and a new file continues the chain.

## Configuration file

```json
{
  "enabled": true,
  "defaultLevel": "inform",
  "sources": {"vla-engine": "propose", "voice-ui": "execute_with_confirmation", "semantic-planner": "propose"},
  "auditFile": "/var/lib/hydra-umc/cognitive/autonomy-audit.jsonl",
  "auditMaxBytes": 10485760,
  "auditMemory": 200
}
```

A misspelt key stops the start with a message.

## What has and has not been tried

The policy and the routes run and are tested with requests that stand in for the services. The VLA engine (`serve --cognitive-node-url`) and the voice interface (`HYDRA_UMC_VOICE_UI_COGNITIVE_URL`) can ask before they hand out a confirmation, each with its `subjectId` and, with a proof key, the `confirmationProof`; both are off by default and treat anything but `allow` as a refusal. Wiring the semantic planner and the server is still open, and none of this has run against a real cell.

## Confirmation proof (off by default)

`"confirmationProof": {"required": true, "approvalKeyFile": "...", "voiceKeyFile": "..."}` makes `execute_with_confirmation` need more than `humanConfirmed`: the question carries `subjectId` (the robot or machine) and `confirmationProof`, the `ConfirmationProof` of HYDRA-UMC-SDK that the VLA engine (`kind` `approval`) or the voice interface (`kind` `voice`) signed with the key of that file. It must be genuine, current, for this `actionId` and `subjectId`, and it is accepted once (the memory of used proofs lives in the process). Otherwise the answer is `proof_required` or `proof_invalid`.
