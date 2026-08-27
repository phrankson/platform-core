# How to deploy a stack

## 1. Select the stack

```console
$ pulumi stack select <platform-sandbox|app-dev|app-prod>
```

## 2. Preview

```console
$ pulumi preview
```

Confirm the resources listed are what you expect: a Docker network, a
Kind cluster (via `local.Command`, not a native Pulumi resource type — see
[Architecture and design choices](../explanation/architecture-and-design-choices.md#why-localcommand-instead-of-a-native-resource-type)),
an Argo CD Helm release, and a root Argo `Application`.

## 3. Apply

```console
$ pulumi up
```

This will:

1. Create (or confirm) the Docker network at the CIDR declared in
   `Pulumi.<stack>.yaml`.
2. Create the Kind cluster, attached to that network.
3. Fetch its kubeconfig and build a Kubernetes provider from it.
4. Install Argo CD via Helm.
5. Create the root Argo `Application`, pointing Argo CD at
   `platform-gitops`'s `environments/<stack>` folder.

Expect this to take several minutes — pulling the Kind node image and
waiting for the cluster to report ready is the slowest step.

## 4. Verify

```console
$ pulumi stack output
$ kubectl --kubeconfig <(pulumi stack output kubeconfig --show-secrets) get nodes
$ kubectl --kubeconfig <(pulumi stack output kubeconfig --show-secrets) get applications -n argocd
```

Or run the full integration test suite — see
[Run integration tests](run-integration-tests.md).

## If you're running more than one stack's cluster at once

Creating a new Kind cluster while another one (also on
`KIND_EXPERIMENTAL_DOCKER_NETWORK`) is still mid-bootstrap can cause the
new cluster's worker node to fail joining. See
[Troubleshooting](troubleshooting.md#a-new-cluster-fails-to-join-its-own-worker-node)
before running `pulumi up` on a stack that doesn't have a cluster yet
while others are running.
