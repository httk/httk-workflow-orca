#!/usr/bin/env bash

# Native httk ORCA Bash API, version 1. Source httk-workflow.sh first.
#
# Every function is one orca-* bridge subcommand, and every option of that
# subcommand is available here: the arguments are passed through untouched.
#
#   httk_orca_write_input --options OPTIONS.json [--input orca.inp]
#   httk_orca_run [--directory .] [--input orca.inp] [--output orca.out] [--timeout S] -- /abs/path/orca
#       prints the report path; exits 0 completed, 20 crashed, 21 nonconverged,
#       22 process failure, 124 timeout
#   httk_orca_energy [--output orca.out] [--unit eh|ev]   exits 1 when there is no energy
#   httk_orca_converged [--output orca.out]               exits 1 when not converged
#   httk_orca_diagnose [--output orca.out] [--json]       exits 20 when it found anything
HTTK_ORCA_BASH_API_VERSION=1

_httk_orca_require_workflow_api() {
    if ! declare -F _httk_workflow_bridge >/dev/null 2>&1; then
        printf 'httk-workflow: source HTTK_WORKFLOW_BASH_API before HTTK_WORKFLOW_ORCA_BASH_API\n' >&2
        return 2
    fi
}

httk_orca_write_input() {
    _httk_orca_require_workflow_api || return
    _httk_workflow_bridge orca-write-input "$@"
}

httk_orca_run() {
    _httk_orca_require_workflow_api || return
    _httk_workflow_bridge orca-run "$@"
}

httk_orca_energy() {
    _httk_orca_require_workflow_api || return
    _httk_workflow_bridge orca-energy "$@"
}

httk_orca_converged() {
    _httk_orca_require_workflow_api || return
    _httk_workflow_bridge orca-converged "$@"
}

httk_orca_diagnose() {
    _httk_orca_require_workflow_api || return
    _httk_workflow_bridge orca-diagnose "$@"
}
