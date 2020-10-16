"""Pytest plugin implementing a Node fixture for running remote commands."""
from __future__ import annotations

import json
import logging
import typing
from io import BytesIO
from uuid import uuid4

import fabric  # type: ignore
import invoke  # type: ignore
from fabric import Connection
from invoke import Context
from invoke.runners import Result  # type: ignore
from tenacity import retry, stop_after_delay, wait_exponential  # type: ignore

import pytest

if typing.TYPE_CHECKING:
    from typing import Any, Dict, Iterator, Optional, Tuple

    from _pytest.fixtures import FixtureRequest

# Setup a sane configuration for local and remote commands. Note that
# the defaults between Fabric and Invoke are different, so we use
# their Config classes explicitly.
config = {
    "run": {
        # Show each command as its run.
        "echo": True,
        # Disable stdin forwarding.
        "in_stream": False,
        # Don’t let remote commands take longer than five minutes
        # (unless later overridden). This is to prevent hangs.
        "timeout": 300,
    }
}


# Provide a configured local Invoke context for running commands
# before establishing a connection. (Use like `local.run(...)`).
invoke_config = invoke.Config(overrides=config)
local = Context(config=invoke_config)


def check_az_cli() -> None:
    """Assert that the `az` CLI is installed and logged in."""
    # E.g. on Ubuntu: `curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash`
    assert local.run("az --version", warn=True), "Please install the `az` CLI!"
    # TODO: Login with service principal (az login) and set
    # default subscription (az account set -s) using secrets.
    account: Result = local.run("az account show")
    assert account.ok, "Please `az login`!"
    sub = json.loads(account.stdout)
    assert sub["isDefault"], "Please `az account set -s <subscription>`!"
    logging.info(
        f"Using account '{sub['user']['name']}' with subscription '{sub['name']}'"
    )


def create_boot_storage(location: str) -> str:
    """Create a separate resource group and storage account for boot diagnostics."""
    account = "pytestbootdiag"
    # This command always exits with 0 but returns a string.
    if local.run("az group exists -n pytest-lisa").stdout.strip() == "false":
        local.run(f"az group create -n pytest-lisa --location {location}")
    if not local.run(f"az storage account show -g pytest-lisa -n {account}", warn=True):
        local.run(f"az storage account create -g pytest-lisa -n {account}")
    return account


def deploy_vm(
    name: str,
    location: str = "westus2",
    vm_image: str = "UbuntuLTS",
    vm_size: str = "Standard_DS1_v2",
    setup: str = "",
    networking: str = "",
) -> Tuple[str, Dict[str, str]]:
    """Given deployment info, deploy a new VM.

    TODO: This along with the functions it calls are Azure specific
    and so would be refactored to support other platforms. Hence it
    returns both the host and the deployment data so that calling
    functions don't have to know which field in the data corresponds
    to the host.

    """
    check_az_cli()
    boot_storage = create_boot_storage(location)

    logging.info(
        f"Deploying VM to resource group '{name}-rg' in '{location}' with image '{vm_image}' and size '{vm_size}'"
    )

    local.run(f"az group create -n {name}-rg --location {location}")

    vm_command = [
        "az vm create",
        f"-g {name}-rg",
        f"-n {name}",
        f"--image {vm_image}",
        f"--size {vm_size}",
        f"--boot-diagnostics-storage {boot_storage}",
        "--generate-ssh-keys",
    ]
    if networking == "SRIOV":
        vm_command.append("--accelerated-networking true")

    data: Dict[str, str] = json.loads(local.run(" ".join(vm_command)).stdout)
    host = data["publicIpAddress"]
    return host, data


def delete_vm(name: str) -> None:
    """Delete the entire allocated resource group."""
    # TODO: Maybe don’t wait for this command to complete.
    logging.info(f"Deleting resource group '{name}-rg'")
    local.run(f"az group delete -n {name}-rg --yes")


class Node(Connection):
    """Extends 'fabric.Connection' with our own utilities."""

    name: str
    data: Dict[str, str]

    def local(self, *args: Any, **kwargs: Any) -> Result:
        """This patches Fabric's 'local()' function to ignore SSH environment."""
        return super(Connection, self).run(replace_env=False, env={}, *args, **kwargs)

    @retry(wait=wait_exponential(), stop=stop_after_delay(60))
    def get_boot_diagnostics(self) -> Result:
        """Gets the serial console logs."""
        return self.local(
            f"az vm boot-diagnostics get-boot-log -n {self.name} -g {self.name}-rg"
        )

    def platform_restart(self) -> Result:
        """TODO: Should this '--force' and redeploy?"""
        return self.local(f"az vm restart -n {self.name} -g {self.name}-rg")

    def cat(self, path: str) -> str:
        """Gets the value of a remote file without a temporary file."""
        with BytesIO() as buf:
            self.get(path, buf)
            return buf.getvalue().decode("utf-8").strip()


@pytest.fixture
def node(request: FixtureRequest) -> Iterator[Node]:
    """Yields a safe remote Node on which to run commands.

    TODO: Currently this also manages the caching of the deployed VMs.
    However, we should make a node pool (perhaps a session-scoped
    fixture) which caches and deploys VMs, leaving this to perform its
    original work as a connection creator.

    """
    deploy_marker = request.node.get_closest_marker("deploy")
    connect_marker = request.node.get_closest_marker("connect")

    data: Dict[str, str] = dict()
    name: Optional[str] = None
    host: Optional[str] = None

    # TODO: The deploy and connect markers should be mutually
    # exclusive.
    if deploy_marker:
        # NOTE: https://docs.pytest.org/en/stable/cache.html
        key = "/".join(["node"] + list(filter(None, deploy_marker.kwargs.values())))
        assert request.config.cache is not None
        data = request.config.cache.get(key, None)
        if data:
            logging.info(f"Reusing node for cached key '{key}'")
        else:
            # Cache miss, deploy new node...
            name = f"pytest-{uuid4()}"
            host, data = deploy_vm(name, **deploy_marker.kwargs)
            data["name"] = name
            data["host"] = host
            request.config.cache.set(key, data)
        name = data["name"]
        host = data["host"]
    elif connect_marker:
        # Get the host from the test’s marker.
        host = connect_marker.args[0]
        name = f"pre-deployed:{host}"
    else:
        # NOTE: This still uses SSH so the localhost must be
        # connectable.
        host = "localhost"
        name = host

    # Yield the configured Node connection.
    ssh_config: Dict[str, Any] = config.copy()
    ssh_config["run"]["env"] = {
        # Set PATH since it’s not a login shell.
        "PATH": "/sbin:/usr/sbin:/usr/local/sbin:/bin:/usr/bin:/usr/local/bin"
    }
    fabric_config = fabric.Config(overrides=ssh_config)
    with Node(host, config=fabric_config, inline_ssh_env=True) as n:
        n.name = name
        n.data = data
        yield n

    # Clean up!
    if not request.config.getoption("keep_vms") and key:
        delete_vm(name)
        assert request.config.cache is not None
        request.config.cache.set(key, None)
