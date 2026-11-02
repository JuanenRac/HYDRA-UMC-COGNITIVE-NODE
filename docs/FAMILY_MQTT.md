# The family on a retained MQTT topic

Off by default. Without `--mqtt-config FILE` (or `HYDRA_UMC_COGNITIVE_NODE_MQTT_CONFIG`), or with `"enabled": false` in it, the node publishes nothing.

With it on, the node publishes what `GET /family-status` answers to one **retained** topic, `hydra/cognitive/family` by default, so the Studio, the Suite and the phones read the state of the family without asking the node. It publishes when the content changes and once more every `refreshSeconds` (a client that subscribes late and a broker that lost its retained messages both recover). When the node stops it publishes `{"online": false, "schema": "1.0"}` on the same topic.

## Payload

```json
{"schema": "1.0", "online": true, "sharedModelsPresent": false, "allChildrenPresent": true, "allChildrenHealthy": true,
 "children": [{"name": "HYDRA-UMC-VLA-ENGINE", "present": true, "version": "0.1.0", "maturity": "functional",
               "health": {"reachable": true, "healthy": true, "http_status": 200, "latency_ms": 4}}]}
```

`health` and `allChildrenHealthy` appear only with `"probe": true` in the configuration (the node then asks each child, as `family-status --probe` does). The payload names no path, address or token.

## Broker

The messages go out with the smallest MQTT 3.1.1 publisher that does the job (connect, publish at QoS 0, disconnect), with no dependency. A broker that is not on this machine needs `"tls": true` (with `caFile` for a private authority), or `"allowPlaintext": true` set on purpose. The user name and the password are read from `usernameFile` and `passwordFile`, never from the configuration itself. A broker that is down is counted (`GET /family-mqtt` shows the messages published and failed and the last error) and the next look tries again.

## Configuration file

```json
{
  "enabled": true,
  "broker": "127.0.0.1:1883",
  "tls": false,
  "caFile": null,
  "clientId": "hydra-umc-cognitive-node",
  "usernameFile": null,
  "passwordFile": null,
  "allowPlaintext": false,
  "timeoutSeconds": 5,
  "topic": "hydra/cognitive/family",
  "intervalSeconds": 10,
  "refreshSeconds": 300,
  "probe": false
}
```

A topic with a wildcard, or one that starts with `$`, is refused. A misspelt key stops the start with a message.

## What has and has not been tried

Tested against a stand-in broker that answers CONNACK and keeps the packets, and with the publisher driven by a clock. It has not been tried against the broker of the ecosystem, and the Studio and the phones do not subscribe to the topic yet.
