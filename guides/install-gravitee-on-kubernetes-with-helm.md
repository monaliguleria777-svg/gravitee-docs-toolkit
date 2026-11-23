---
description: Install Gravitee on a local Kubernetes cluster with Helm, for development and testing.
---

# Install Gravitee on a local Kubernetes cluster with Helm

This guide installs Gravitee API Management on a Kubernetes cluster on your own computer. When you finish, you can sign in to the APIM Console, the Developer Portal and the Gateway in your browser.

{% hint style="warning" %}
This setup is for development and testing only. It turns off authentication and storage persistence for MongoDB and Elasticsearch, so data is lost when pods restart.
{% endhint %}

## Before you begin

You need:

* Docker Desktop with Kubernetes turned on (**Settings > Kubernetes > Enable Kubernetes**), or minikube
* `kubectl`, the Kubernetes command-line tool
* `helm`, the Kubernetes package manager
* About 8 GB of memory free for Docker

Check that your cluster is running:

```bash
kubectl get nodes
```

You see one node with the status `Ready`.

## Overview

Gravitee stores its configuration in MongoDB and its analytics in Elasticsearch. The Gravitee Helm chart doesn't include these, so you install them first:

1. Create a namespace.
2. Install MongoDB.
3. Install Elasticsearch.
4. Install an ingress controller and add local hostnames.
5. Install Gravitee.
6. Check the installation.

## 1. Create a namespace

A namespace keeps all the Gravitee resources together, so you can remove them in one step later.

```bash
kubectl create namespace gravitee-gamma
```

## 2. Install MongoDB

```bash
helm install gravitee-mongodb oci://registry-1.docker.io/cloudpirates/mongodb \
  --namespace gravitee-gamma \
  --set auth.enabled=false \
  --set persistence.enabled=false \
  --set resources.requests.memory=512Mi \
  --set resources.requests.cpu=250m
```

## 3. Install Elasticsearch

1. Add the Elastic Helm repository:

   ```bash
   helm repo add elastic https://helm.elastic.co
   helm repo update
   ```

2. Install a single Elasticsearch node:

   ```bash
   helm install elasticsearch elastic/elasticsearch \
     --namespace gravitee-gamma \
     --set persistence.enabled=false \
     --set replicas=1 \
     --set minimumMasterNodes=1
   ```

3. Copy the generated password. You need it in step 5.

   ```bash
   kubectl get secrets --namespace gravitee-gamma elasticsearch-master-credentials \
     -o jsonpath='{.data.password}' | base64 -d
   ```

## 4. Set up ingress and local hostnames

An ingress controller routes browser traffic to the right Gravitee service.

1. Install the NGINX ingress controller.

   {% tabs %}
   {% tab title="Docker Desktop" %}
   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/cloud/deploy.yaml
   ```
   {% endtab %}

   {% tab title="minikube" %}
   ```bash
   minikube addons enable ingress
   sudo minikube tunnel
   ```

   Keep the `minikube tunnel` terminal open while you use Gravitee.
   {% endtab %}
   {% endtabs %}

2. Add two hostnames to your hosts file (`/etc/hosts` on macOS and Linux, `C:\Windows\System32\drivers\etc\hosts` on Windows):

   ```text
   127.0.0.1 gamma.localhost
   127.0.0.1 api.localhost
   ```

## 5. Install Gravitee

1. Create a file called `values.yaml`. Replace `<ELASTICSEARCH_PASSWORD>` with the password from step 3.

   ```yaml
   # Use the MongoDB and Elasticsearch you installed, not bundled ones
   mongodb:
     enabled: false
   elasticsearch:
     enabled: false

   mongo:
     uri: mongodb://gravitee-mongodb.gravitee-gamma.svc.cluster.local:27017/gravitee

   es:
     endpoints:
       - https://elasticsearch-master:9200
     security:
       enabled: true
       username: elastic
       password: <ELASTICSEARCH_PASSWORD>

   gamma:
     enabled: true
   gammaUi:
     enabled: true

   installation:
     api:
       url: http://gamma.localhost/management
   ```

   {% hint style="info" %}
   This is a shortened `values.yaml`. Gravitee's full example also sets image tags and ingress hosts for each component. If a component doesn't start, compare your file with the example in the official installation guide.
   {% endhint %}

2. Add the Gravitee Helm repository and list the available chart versions:

   ```bash
   helm repo add graviteeio https://helm.gravitee.io
   helm repo update
   helm search repo graviteeio/apim --devel --versions
   ```

3. Install Gravitee. Replace `<VERSION>` with a version from the previous command. The release name must be `gamma`.

   ```bash
   helm install gamma graviteeio/apim \
     --version <VERSION> --devel \
     --namespace gravitee-gamma \
     -f values.yaml \
     --wait --timeout 10m
   ```

   The command finishes when all components are ready. This can take up to 10 minutes the first time, while Docker downloads the images.

## 6. Check the installation

1. Check that all pods are running:

   ```bash
   kubectl get pods --namespace gravitee-gamma
   ```

   Each Gravitee pod (`gamma-apim-api`, `gamma-apim-gateway`, `gamma-apim-ui`, `gamma-apim-portal`, `gamma-gamma`) shows `1/1` and `Running`.

2. Check that the Management API responds:

   ```bash
   curl -s -u admin:admin http://gamma.localhost/management/organizations/DEFAULT/environments
   ```

   You see a JSON list of environments.

3. Open Gravitee in your browser and sign in with the username `admin` and password `admin`:

   | Component | URL |
   |---|---|
   | Gravitee console | http://gamma.localhost/ |
   | APIM Console | http://gamma.localhost/console |
   | Developer Portal | http://gamma.localhost/dev/ |
   | Gateway | http://api.localhost/ |

{% hint style="danger" %}
`admin` / `admin` is the default login. Change it before anyone else can reach your cluster.
{% endhint %}

## Troubleshooting

<!-- Fill this in from your own install: every error you hit, what caused it, and the fix. -->

| Problem | Cause | Fix |
|---|---|---|
| A pod stays in `Pending` | Docker doesn't have enough memory | Increase Docker Desktop's memory to at least 8 GB |
| `gamma.localhost` doesn't load | Hostnames missing from the hosts file, or ingress not ready | Repeat step 4 and run `kubectl get pods -n ingress-nginx` |

## Remove everything

```bash
helm uninstall gamma elasticsearch gravitee-mongodb --namespace gravitee-gamma
kubectl delete namespace gravitee-gamma
```

## Next steps

* Create your first API in the APIM Console.
* Expose a Kafka topic through Gravitee: see [Expose Kafka events as an HTTP API with Gravitee](expose-kafka-events-with-gravitee.md).

---

*Based on Gravitee's official Kubernetes installation guide (Gravitee Gamma 4.12, pre-release documentation, November 2026). Tested on: \_\_\_ (add your OS, Docker Desktop version and chart version after you run it).*
