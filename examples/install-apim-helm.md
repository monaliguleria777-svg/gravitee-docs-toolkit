---
description: Install gravitee API management on Kubernetes with helm.
---

# Install API Management On Kubernetes Using Helm.

This guide shows you how to quickly install the gravitee gateway and the Developer portal on a local kubernetes cluster, e.g. one created with Docker Desktop, so that you can easily try out the product, test your first API and see how policies are applied to the traffic that passes through the gateway before you move to a production environment.

{% hint style="note" %}
You need Helm 3 and a running Kubernetes cluster.
{% endhint %}

## Prerequisites

* Docker Desktop with Kubernetes turned on
* Helm 3

## Add the Gravitee Helm repository

1. Add the repository:

```
helm repo add graviteeio https://helm.gravitee.io
helm repo update
```

2. Click on the **Clusters** tab to check your cluster is running.

![](../assets/cluster.png)

{% tabs %}
{% tab title="Default values" %}
Install with the default values. For more options see [here](https://documentation.gravitee.io).
{% endtab %}
