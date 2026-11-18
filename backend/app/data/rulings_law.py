"""Default corpus of TNT-LAW-01. Every record was written for this demo."""

from __future__ import annotations

from ..models import Matter, Outcome

C, L = Matter.COMMERCIAL, Matter.LABOUR
BENCH = "Meridian Commercial Disputes Bench"
PANEL = "Valdorian Trade Appeals Panel"
BOARD = "Halden Labour Review Board"
VENTHAME, ASHDALE, TARROW = "Judge Orla Venthame", "Judge Corwin Ashdale", "Judge Maelis Tarrow"

#: (sequence, title, authority, matter, date, outcome, exposure in GBP, articles, officer, summary)
ROWS: tuple[tuple, ...] = (
    (1, "Corvane Freight v Lumestra Packaging", BENCH, C, "2024-03-12", Outcome.UPHELD, 412_000,
     ["COC art. 14", "COC art. 31"], VENTHAME,
     "Late delivery of cold-chain equipment triggered the liquidated damages clause; the "
     "supplier's force majeure notice was served out of time."),
    (2, "Pellwick Foods v Dravos Cold Storage", BENCH, C, "2024-06-27", Outcome.DISMISSED, 95_500,
     ["COC art. 14", "COC art. 52"], ASHDALE,
     "Claim for spoiled stock failed: the warranty of fitness excluded losses caused by the "
     "buyer's own temperature settings."),
    (3, "Quenthar Mutual v Osmere Software", PANEL, C, "2024-09-05", Outcome.SETTLED_WITH_COSTS,
     230_000, ["COC art. 31", "COC art. 77"], TARROW,
     "Dispute over termination for convenience of a licensing agreement settled on appeal; "
     "the respondent bears the costs of both instances."),
    (4, "Brindlow Textiles v Vantry Logistics", BENCH, C, "2025-01-21", Outcome.UPHELD, 688_250,
     ["COC art. 14", "COC art. 31", "COC art. 77"], VENTHAME,
     "Exclusive supply arrangement breached by parallel deliveries; damages follow the "
     "liquidated damages clause without reduction."),
    (5, "Kilnwarth Energy v Sablewood Works", PANEL, C, "2025-04-30", Outcome.DISMISSED, 54_000,
     ["COC art. 52"], TARROW,
     "Appeal against a set-off dismissed: the limitation clause was drafted in plain terms "
     "and brought to the buyer's attention."),
    (6, "Zephran Systems v Ulverith Holdings", BENCH, C, "2025-08-14", Outcome.SETTLED_WITH_COSTS,
     147_300, ["COC art. 31"], ASHDALE,
     "Software delivery milestones were missed by both sides; the parties settled and the "
     "claimant recovers its costs."),
    (7, "Workforce Council of Halsk Works v Halsk Works", BOARD, L, "2024-05-16", Outcome.UPHELD,
     128_000, ["LRS s. 22", "LRS s. 40"], TARROW,
     "Redundancy consultation started after the decision to close the line; the protective "
     "award is upheld in full."),
    (8, "Fenmoor Logistics Staff Panel v Fenmoor Logistics", BOARD, L, "2024-11-08",
     Outcome.DISMISSED, 36_750, ["LRS s. 22"], ASHDALE,
     "Unpaid overtime claim dismissed: the rota records showed the hours had been "
     "compensated with time off in lieu."),
    (9, "Tavrik Foods Drivers' Committee v Tavrik Foods", BOARD, L, "2025-03-19", Outcome.UPHELD,
     84_600, ["LRS s. 40", "LRS s. 58"], VENTHAME,
     "Non-compete covenant held unenforceable beyond six months; unfair dismissal of two "
     "drivers upheld with compensation."),
    (10, "Elswen Mutual Employees' Forum v Elswen Mutual", BOARD, L, "2025-10-02",
     Outcome.SETTLED_WITH_COSTS, 61_900, ["LRS s. 22", "LRS s. 58"], TARROW,
     "Fixed-term renewals treated as a continuous post; the employer settled and pays the "
     "forum's costs."),
)
