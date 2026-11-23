---
description: Run Kafka locally, then expose a Kafka topic as an HTTP API through the Gravitee Gateway.
---

# Expose Kafka events as an HTTP API with Gravitee

Kafka is a platform for streaming events, such as "order placed" or "payment received". Applications write events to a **topic**, and other applications read them. To read from Kafka directly, an application needs a Kafka client library and network access to the Kafka cluster.

Gravitee puts an API in front of Kafka, so applications can send and receive events over plain HTTP. Gravitee also adds security plans, analytics and a listing in the Developer Portal.

This guide has two parts:

1. **Run Kafka locally** and send your first events. You don't need Gravitee for this part.
2. **Expose the topic through Gravitee** as a Message API.

## Before you begin

* Docker Desktop
* For part 2: Gravitee running locally (see [Install Gravitee on a local Kubernetes cluster with Helm](install-gravitee-on-kubernetes-with-helm.md))

{% hint style="warning" %}
Creating a Message API needs a Gravitee licence that includes the `apim-en-message-reactor` feature. Without it, the APIM Console shows an upgrade message when you select **Create Message API**. Part 1 works without a licence.
{% endhint %}

## Part 1: Run Kafka and send events

1. Start a single Kafka broker in Docker:

   ```bash
   docker run -d --name kafka -p 9092:9092 apache/kafka:3.9.0
   ```

2. Create a topic called `orders`:

   ```bash
   docker exec kafka /opt/kafka/bin/kafka-topics.sh \
     --create --topic orders --bootstrap-server localhost:9092
   ```

   You see `Created topic orders.`

3. Open a second terminal and start a consumer. It waits and prints every event written to `orders`:

   ```bash
   docker exec -it kafka /opt/kafka/bin/kafka-console-consumer.sh \
     --topic orders --from-beginning --bootstrap-server localhost:9092
   ```

4. In the first terminal, start a producer and type two events, pressing Enter after each:

   ```bash
   docker exec -it kafka /opt/kafka/bin/kafka-console-producer.sh \
     --topic orders --bootstrap-server localhost:9092
   ```

   ```text
   {"orderId": 1, "status": "placed"}
   {"orderId": 2, "status": "paid"}
   ```

   Both events appear in the consumer terminal.

5. Press **Ctrl+C** in both terminals to stop the producer and consumer.

## Part 2: Expose the topic through Gravitee

In this part you create a **Message API**. Clients send events with HTTP POST, and Gravitee's Kafka endpoint writes them to the `orders` topic.

1. In the APIM Console, go to **Event Stream Management > Message APIs** and select **Create Message API**.
2. **Details:** enter the name `Orders events` and keep the version `1.0`.
3. **Entrypoints:** select **HTTP POST**. Set the context path to `/orders`.

   {% hint style="info" %}
   The context path must start with `/`, be longer than three characters, and use only letters, numbers, `/`, `.`, `-` and `_`.
   {% endhint %}

4. **Endpoints:** select **Kafka**. In the connection settings, enter the bootstrap server and the topic `orders`.

   <!-- TODO: confirm the exact field names in the Console and the bootstrap address Gravitee can reach from inside the cluster (for example host.docker.internal:9092 on Docker Desktop). Kafka may also need its advertised listener changed so pods can reach it. -->

5. **Security:** keep the default **Keyless** plan for this test.

   {% hint style="danger" %}
   A keyless plan lets anyone call the API. Use it for local testing only, and add an API key or OAuth2 plan before sharing the API.
   {% endhint %}

6. **Review:** select **Deploy now**, then **Create Message API**.

### Send an event through Gravitee

1. Start the Kafka consumer from Part 1, step 3.
2. Send an event to the Gateway:

   ```bash
   curl -X POST http://api.localhost/orders \
     -H "Content-Type: application/json" \
     -d '{"orderId": 3, "status": "shipped"}'
   ```

3. Check the consumer terminal. The event `{"orderId": 3, "status": "shipped"}` appears, which shows it travelled from HTTP, through the Gravitee Gateway, into Kafka.

## Troubleshooting

| Problem | Cause | Fix |
|---|---|---|
| Docker shows "Virtual Machine Platform is not enabled" (Windows) | A Windows feature that WSL 2 needs is turned off | In PowerShell as administrator, run `Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All`, then restart Windows |
| `docker` commands fail with "500 Internal Server Error" or "cannot find the file specified" | The Docker Desktop engine isn't running | Open Docker Desktop and wait for **Engine running** before running commands |
| **Create Message API** shows an upgrade message | Your licence doesn't include message APIs | Request a licence that includes `apim-en-message-reactor` |
| The event doesn't reach Kafka | The Gateway pod can't reach the broker | Check the bootstrap address and Kafka's advertised listener |

## Clean up

```bash
docker rm -f kafka
```

---

*Part 1 tested on Windows with Docker Desktop 29.9.3 and Kafka 3.9.0, 23 Nov 2026. Part 2 (Gravitee Message API) not yet tested – it needs a Gravitee licence.*
