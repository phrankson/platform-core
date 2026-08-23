#!/usr/bin/env bats
# Infrastructure validation tests for the local Kind cluster.
#
# Run after `pulumi up` to confirm the deployed infrastructure is actually
# reachable, not just reported as created by Pulumi.
#
# Usage:
#   export PULUMI_STACK=platform-sandbox   # optional; defaults to the
#                                           # currently selected stack
#   bats tests/integration/infrastructure.bats

setup_file() {
    # Run once before all tests.
    PULUMI_STACK="${PULUMI_STACK:-$(pulumi stack --show-name)}"

    pulumi stack output kubeconfig --show-secrets --stack "$PULUMI_STACK" > kubeconfig.yaml
    export KUBECONFIG="$PWD/kubeconfig.yaml"
    export DOCKER_NETWORK=$(pulumi stack output docker_network --stack "$PULUMI_STACK")
    export CLUSTER_NAME=$(pulumi stack output cluster_name --stack "$PULUMI_STACK")
}

teardown_file() {
    # Cleanup after all tests, so we don't leave a stray config file
    # that would affect testing in other environments.
    rm -f kubeconfig.yaml
}

@test "docker network exists" {
    run docker network inspect "$DOCKER_NETWORK"
    [ "$status" -eq 0 ]
}

@test "kubernetes cluster is accessible" {
    run kubectl get nodes --no-headers
    [ "$status" -eq 0 ]
    node_count=$(echo "$output" | wc -l)
    [ "$node_count" -ge 1 ]
}
