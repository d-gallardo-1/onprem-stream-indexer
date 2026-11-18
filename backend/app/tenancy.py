"""The tenant scoping layer.

``TenantStore.partition`` is the only way to obtain tenant data. Every read,
search, stream, crawl and export starts by calling it with the tenant ID of the
request, and works on the partition it returns. An unknown ID raises
``UnknownTenant``, which the API answers with 404.

This is data partitioning, not access control: the demo has no authentication,
so the caller chooses the tenant. What this layer guarantees is that, once a
tenant is named, the request can only ever touch that tenant's records.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Iterable

from .data.tenants import TENANT_PROFILES, TenantProfile
from .models import Tenant
from .partition import TenantPartition


class UnknownTenant(LookupError):
    """The tenant ID does not exist."""


class TenantStore:
    def __init__(self, profiles: Iterable[TenantProfile] = TENANT_PROFILES, *,
                 clock: Callable[[], datetime]) -> None:
        self._profiles = tuple(profiles)
        self._clock = clock
        self._partitions: dict[str, TenantPartition] = {}
        self.reset()

    @property
    def tenants(self) -> list[Tenant]:
        return [profile.tenant for profile in self._profiles]

    def partition(self, tenant_id: str) -> TenantPartition:
        try:
            return self._partitions[tenant_id]
        except KeyError:
            raise UnknownTenant(tenant_id) from None

    def reset(self) -> None:
        """Rebuild every partition from the default corpus."""
        self._partitions = {
            profile.tenant.tenant_id: TenantPartition(profile, self._clock)
            for profile in self._profiles
        }
