"""The two demo tenants and the invented authorities each one follows.

No authority, statute, portal or person named in this package exists. Docket
identifiers start with ``SYN-`` so that no record can be read as a decision of
a real body. Any resemblance to a real name is coincidental.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..models import Matter, Tenant


@dataclass(frozen=True)
class TenantProfile:
    tenant: Tenant
    #: Middle part of every docket identifier of this tenant: ``SYN-<code>-...``.
    code: str
    #: Authority that decides each matter this tenant follows.
    authorities: dict[Matter, tuple[str, ...]]
    #: Invented statute each matter cites, with its abbreviation.
    statutes: dict[Matter, str]
    officers: tuple[str, ...]


LAW = TenantProfile(
    tenant=Tenant(
        tenant_id="TNT-LAW-01",
        name="Vanguard Corporate Litigation LLP",
        focus="Commercial and labour rulings",
    ),
    code="LAW",
    authorities={
        Matter.COMMERCIAL: ("Meridian Commercial Disputes Bench", "Valdorian Trade Appeals Panel"),
        Matter.LABOUR: ("Halden Labour Review Board",),
    },
    statutes={
        Matter.COMMERCIAL: "Commercial Obligations Code (COC)",
        Matter.LABOUR: "Labour Relations Statute (LRS)",
    },
    officers=("Judge Orla Venthame", "Judge Corwin Ashdale", "Judge Maelis Tarrow"),
)

INDUSTRIAL = TenantProfile(
    tenant=Tenant(
        tenant_id="TNT-IND-02",
        name="NorthSea Infrastructure Compliance",
        focus="Industrial safety and machinery enforcement",
    ),
    code="IND",
    authorities={
        Matter.INDUSTRIAL_SAFETY: ("Kestrel Industrial Safety Inspectorate",
                                   "Harbour Works Enforcement Tribunal"),
        Matter.MACHINERY: ("Arvenmark Machinery Conformity Office",),
    },
    statutes={
        Matter.INDUSTRIAL_SAFETY: "Industrial Safety Code (ISC)",
        Matter.MACHINERY: "Machinery Conformity Rules (MCR)",
    },
    officers=("Inspector Tavin Rooke", "Inspector Sabel Wynmoor", "Judge Edrin Calloway"),
)

TENANT_PROFILES: tuple[TenantProfile, ...] = (LAW, INDUSTRIAL)

MATTER_LABELS: dict[Matter, str] = {
    Matter.COMMERCIAL: "Commercial",
    Matter.LABOUR: "Labour",
    Matter.INDUSTRIAL_SAFETY: "Industrial safety",
    Matter.MACHINERY: "Machinery",
}
