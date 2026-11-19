# Copyright The OpenTelemetry Authors
# SPDX-License-Identifier: Apache-2.0

from enum import Enum
from typing import Final

HOST_ARCH: Final = "host.arch"
"""
The CPU architecture the host system is running on.
"""

HOST_CPU_CACHE_L2_SIZE: Final = "host.cpu.cache.l2.size"
"""
The amount of level 2 memory cache available to the processor (in Bytes).
"""

HOST_CPU_FAMILY: Final = "host.cpu.family"
"""
Family or generation of the CPU.
"""

HOST_CPU_MODEL_ID: Final = "host.cpu.model.id"
"""
Model identifier. It provides more granular information about the CPU, distinguishing it from other CPUs within the same family.
"""

HOST_CPU_MODEL_NAME: Final = "host.cpu.model.name"
"""
Model designation of the processor.
"""

HOST_CPU_STEPPING: Final = "host.cpu.stepping"
"""
Stepping or core revisions.
"""

HOST_CPU_VENDOR_ID: Final = "host.cpu.vendor.id"
"""
Processor manufacturer identifier. A maximum 12-character string.
Note: [CPUID](https://wiki.osdev.org/CPUID) command returns the vendor ID string in EBX, EDX and ECX registers. Writing these to memory in this order results in a 12-character string.
"""

HOST_ID: Final = "host.id"
"""
Unique host ID, determined by the first matching source in the priority order.
Note: SHOULD be determined using the first available source from the following priority tiers:

1. Known cloud vendors - cloud instance ID
2. Known VM vendors - provider VM ID
3. OS-dependent machine ID
4. User-provided value

The value SHOULD conform to the following properties:

* **Unique** within a given context;
* **[Repeatable](https://opentelemetry.io/docs/specs/otel/entities/data-model/#repeatable-identity)** - multiple observers on the same host come up with the same value;
* **Persistent** - survives host restarts and software updates.

**Collecting `host.id` From Known Environments:** When `host.id` is derived from a
cloud vendor instance ID, the resource SHOULD also carry the corresponding
`cloud.provider` and `cloud.platform` attributes so that the source of the `host.id`
value can be unambiguously determined.

The following cloud environments are currently recognized:

| Environment | `host.id` source | `cloud.provider` | `cloud.platform` |
| --- | --- | --- | --- |
| AWS EC2 | EC2 instance ID | `aws` | `aws_ec2` |
| AWS EKS (node) | EC2 instance ID | `aws` | `aws_eks` |
| Azure VM | `vmId` | `azure` | `azure.vm` |
| GCP Compute Engine | GCE instance ID | `gcp` | `gcp_compute_engine` |
| GCP GKE (node) | GCE instance ID | `gcp` | `gcp_kubernetes_engine` |

The listed `cloud.provider`/`cloud.platform` values are for example only. Refer to the
[`cloud`](/docs/registry/attributes/cloud.md) attribute definitions for the relevant set of values.

**Non-privileged Machine ID Lookup:** When collecting `host.id` for non-containerized
systems, non-privileged lookups of the machine ID are preferred. SDK detector
implementations MUST use the sources listed below to obtain the machine ID.

| OS | Primary | Fallback |
| --- | --- | --- |
| Linux | contents of `/etc/machine-id` | contents of `/var/lib/dbus/machine-id` |
| BSD | contents of `/etc/hostid` | output of `/bin/kenv -q smbios.system.uuid` |
| macOS | `IOPlatformUUID` line from the output of `/usr/sbin/ioreg -rd1 -c "IOPlatformExpertDevice"` | - |
| Windows | `MachineGuid` from registry `HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Cryptography` | - |

**Privileged Machine ID Lookup:** The `host.id` can be looked up using privileged
sources. For example, Linux systems can use the output of `dmidecode -t system`,
`dmidecode -t baseboard`,
`dmidecode -t chassis`, or read the corresponding data from the filesystem
(e.g. `cat /sys/devices/virtual/dmi/id/product_id`,
`cat /sys/devices/virtual/dmi/id/product_uuid`, etc), however, SDK resource
detector implementations MUST NOT collect `host.id` from privileged sources. If
privileged lookup of `host.id` is required, the value SHOULD be injected via the
`OTEL_RESOURCE_ATTRIBUTES` environment variable.

**Collecting `host.id` From User Configuration:** If none of the above sources yields
a non-empty value, the implementation MAY be unable to determine `host.id`
automatically and SHOULD omit the attribute.
In that case, the `host.id` can only be provided through user configuration
or other available manual options. Users SHOULD ensure that the `host.id` value
conforms to the properties stated above.
"""

HOST_IMAGE_ID: Final = "host.image.id"
"""
VM image ID or host OS image ID. For Cloud, this value is from the provider.
"""

HOST_IMAGE_NAME: Final = "host.image.name"
"""
Name of the VM image or OS install the host was instantiated from.
"""

HOST_IMAGE_VERSION: Final = "host.image.version"
"""
The version string of the VM image or host OS as defined in [Version Attributes](/docs/resource/README.md#version-attributes).
"""

HOST_IP: Final = "host.ip"
"""
Available IP addresses of the host, excluding loopback interfaces.
Note: IPv4 Addresses MUST be specified in dotted-quad notation. IPv6 addresses MUST be specified in the [RFC 5952](https://www.rfc-editor.org/rfc/rfc5952.html) format.
"""

HOST_MAC: Final = "host.mac"
"""
Available MAC addresses of the host, excluding loopback interfaces.
Note: MAC Addresses MUST be represented in [IEEE RA hexadecimal form](https://standards.ieee.org/wp-content/uploads/import/documents/tutorials/eui.pdf): as hyphen-separated octets in uppercase hexadecimal form from most to least significant.
"""

HOST_NAME: Final = "host.name"
"""
Name of the host. On UNIX systems, it may contain what the hostname command returns, or the fully qualified hostname, or another name specified by the user.
"""

HOST_TYPE: Final = "host.type"
"""
Type of host. For Cloud, this must be the machine type.
"""


class HostArchValues(Enum):
    AMD64 = "amd64"
    """AMD64."""
    ARM32 = "arm32"
    """ARM32."""
    ARM64 = "arm64"
    """ARM64."""
    IA64 = "ia64"
    """Itanium."""
    PPC32 = "ppc32"
    """32-bit PowerPC."""
    PPC64 = "ppc64"
    """64-bit PowerPC."""
    S390X = "s390x"
    """IBM z/Architecture."""
    X86 = "x86"
    """32-bit x86."""
