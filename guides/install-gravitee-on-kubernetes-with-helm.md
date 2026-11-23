---
description: Install Gravitee on a local Kubernetes cluster with Helm, for development and testing. Tested on Windows with Docker Desktop.
---

# Install Gravitee on a local Kubernetes cluster with Helm

This guide installs Gravitee API Management on a Kubernetes cluster on your own computer. When you finish, you can sign in to the APIM Console, the Developer Portal and the Gravitee console, and call the Gateway.

{% hint style="warning" %}
This setup is for development and testing only. It turns off authentication and storage persistence for MongoDB and Elasticsearch, so data is lost when pods restart.
{% endhint %}

## Before you begin

You need:

* Docker Desktop with Kubernetes turned on (**Settings > Kubernetes > Enable Kubernetes > Apply & restart**)
* `kubectl`, the Kubernetes command-line tool (Docker Desktop installs it)
* `helm`, the Kubernetes package manager (on Windows: `winget install Helm.Helm`)
* At least 6 GB of memory free for Docker. Gravitee runs seven pods.

Check that your cluster is running:

```bash
kubectl get nodes
```

You see one node, `docker-desktop`, with the status `Ready`.

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
helm install gravitee-mongodb oci://registry-1.docker.io/cloudpirates/mongodb --namespace gravitee-gamma --set auth.enabled=false --set persistence.enabled=false --set resources.requests.memory=512Mi --set resources.requests.cpu=250m
```

Wait until the pod shows `1/1 Running`. This takes 1–3 minutes.

```bash
kubectl get pods -n gravitee-gamma
```

## 3. Install Elasticsearch

1. Add the Elastic Helm repository:

   ```bash
   helm repo add elastic https://helm.elastic.co
   helm repo update
   ```

2. Install a single Elasticsearch node:

   ```bash
   helm install elasticsearch elastic/elasticsearch --namespace gravitee-gamma --set persistence.enabled=false --set replicas=1 --set minimumMasterNodes=1
   ```

   Wait until `elasticsearch-master-0` shows `1/1 Running`. This takes 3–5 minutes.

3. Get the generated password. You need it in step 5.

   {% tabs %}
   {% tab title="Windows PowerShell" %}
   ```powershell
   $p = kubectl get secrets -n gravitee-gamma elasticsearch-master-credentials -o jsonpath='{.data.password}'; [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($p))
   ```
   {% endtab %}

   {% tab title="macOS and Linux" %}
   ```bash
   kubectl get secrets -n gravitee-gamma elasticsearch-master-credentials -o jsonpath='{.data.password}' | base64 -d
   ```
   {% endtab %}
   {% endtabs %}

## 4. Set up ingress and local hostnames

An ingress controller routes browser traffic to the right Gravitee service.

1. Install the NGINX ingress controller:

   ```bash
   kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/controller-v1.12.0/deploy/static/provider/cloud/deploy.yaml
   ```

   The output ends with `ingressclass.networking.k8s.io/nginx created`. Gravitee's settings expect this `nginx` class.

2. Add two hostnames to your hosts file.

   {% tabs %}
   {% tab title="Windows PowerShell" %}
   Open PowerShell **as administrator** (right-click > **Run as administrator**), then run:

   ```powershell
   Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "`n127.0.0.1 gamma.localhost`n127.0.0.1 api.localhost"
   ```
   {% endtab %}

   {% tab title="macOS and Linux" %}
   ```bash
   echo "127.0.0.1 gamma.localhost" | sudo tee -a /etc/hosts
   echo "127.0.0.1 api.localhost" | sudo tee -a /etc/hosts
   ```
   {% endtab %}
   {% endtabs %}

## 5. Install Gravitee

1. Download [`values.yaml`](values.yaml) from this folder. It's Gravitee's official settings file from the [Self-host with Helm guide](https://documentation.gravitee.io/gravitee-gamma/platform-management/install/self-hosted-installation-guides/kubernetes/vanilla-kubernetes). It puts every console and the Management API on `gamma.localhost`, so the login session cookie works over HTTP.

2. Open `values.yaml` and replace `[ELASTIC PASSWORD FROM ES INSTALLATION]` with the password from step 3.

3. Add the Gravitee Helm repository and list the chart versions:

   ```bash
   helm repo add graviteeio https://helm.gravitee.io
   helm repo update
   helm search repo graviteeio/apim --devel --versions
   ```

   {% hint style="info" %}
   Gravitee's guide refers to a 4.12 pre-release chart. In November 2026 the newest `graviteeio/apim` chart was **4.13.6**, and no 4.12 version was listed for it. The 4.12 milestone builds in the search results belong to the older `graviteeio/apim3` chart, so don't use those.
   {% endhint %}

4. From the folder that contains `values.yaml`, install Gravitee. The release name must be `gamma`.

   ```bash
   helm install gamma graviteeio/apim --version 4.13.6 --namespace gravitee-gamma -f values.yaml --wait --timeout 15m
   ```

   The command finishes when all components are ready. The first install can take 10–15 minutes while Docker downloads the images.

## 6. Check the installation

1. Check that all pods are running:

   ```bash
   kubectl get pods -n gravitee-gamma
   ```

   All seven pods show `1/1` and `Running`: `elasticsearch-master-0`, `gravitee-mongodb-0`, `gamma-apim-api`, `gamma-apim-gateway`, `gamma-apim-ui`, `gamma-apim-portal` and `gamma-apim-gamma`.

2. Call the Gateway:

   {% tabs %}
   {% tab title="Windows PowerShell" %}
   ```powershell
   curl.exe -i http://api.localhost/
   ```
   {% endtab %}

   {% tab title="macOS and Linux" %}
   ```bash
   curl -i http://api.localhost/
   ```
   {% endtab %}
   {% endtabs %}

   The response is `No context-path matches the request URI.` That means the Gateway is running and has no APIs yet.

3. Open Gravitee in your browser and select **Sign in** with the username `admin` and password `admin`:

   | Component | URL |
   |---|---|
   | APIM Console | http://gamma.localhost/console |
   | Developer Portal | http://gamma.localhost/dev/ |
   | Gravitee console | http://gamma.localhost/ |

{% hint style="danger" %}
`admin` / `admin` is the default login. Change it before anyone else can reach your cluster.
{% endhint %}

## Troubleshooting

These are the issues found while testing this guide on Windows.

| Problem | Cause | Fix |
|---|---|---|
| Docker shows "Virtual Machine Platform is not enabled" | A Windows feature that WSL 2 needs is turned off | In PowerShell as administrator, run `Enable-WindowsOptionalFeature -Online -FeatureName VirtualMachinePlatform -All`, then restart Windows |
| `helm` is "not recognised" right after installing it | PowerShell hasn't loaded the new program yet | Close every PowerShell window and open a new one |
| `base64 -d` fails in PowerShell | Windows PowerShell has no `base64` command | Use the Windows PowerShell command in step 3 |
| "Access denied" when editing the hosts file | The hosts file is protected | Run PowerShell as administrator |
| `curl` returns an unexpected result in PowerShell | In Windows PowerShell, `curl` is an alias for a different command | Use `curl.exe` |
| No chart version 4.12 for `graviteeio/apim` | The docs refer to a pre-release chart that has since been replaced | Install the current `graviteeio/apim` version (4.13.6 when tested) |
| A pod stays in `Pending` | Docker doesn't have enough memory | Close other apps, or give Docker more memory |
| PowerShell won't accept typing after `kubectl get pods -w` | `-w` keeps watching for changes | Press **Ctrl+C** to stop watching |
| The Developer Portal asks you to sign up | Sign-up is for API consumers | Select **Sign in** and use `admin` / `admin` |

## Remove everything

```bash
helm uninstall gamma elasticsearch gravitee-mongodb --namespace gravitee-gamma
kubectl delete namespace gravitee-gamma
```

## Next steps

* Create your first API in the APIM Console.
* Expose a Kafka topic through Gravitee: see [Expose Kafka events as an HTTP API with Gravitee](expose-kafka-events-with-gravitee.md).

---

*Tested on Windows with Docker Desktop 29.9.3 (Kubernetes v1.36.1), Helm v4.3.2 and Gravitee chart `graviteeio/apim` 4.13.6, 23 Nov 2026. Based on Gravitee's official "Self-host with Helm" guide.*
