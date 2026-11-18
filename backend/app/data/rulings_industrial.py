"""Default corpus of TNT-IND-02. Every record was written for this demo."""

from __future__ import annotations

from ..models import Matter, Outcome

S, M = Matter.INDUSTRIAL_SAFETY, Matter.MACHINERY
INSPECTORATE = "Kestrel Industrial Safety Inspectorate"
TRIBUNAL = "Harbour Works Enforcement Tribunal"
OFFICE = "Arvenmark Machinery Conformity Office"
ROOKE, WYNMOOR, CALLOWAY = "Inspector Tavin Rooke", "Inspector Sabel Wynmoor", "Judge Edrin Calloway"

#: (sequence, title, authority, matter, date, outcome, exposure in GBP, articles, officer, summary)
ROWS: tuple[tuple, ...] = (
    (1, "Inspectorate v Corvane Quay Terminals", INSPECTORATE, S, "2024-02-20",
     Outcome.COMPLIANCE_ORDER, 75_000, ["ISC reg. 31", "ISC reg. 44"], ROOKE,
     "Crane exclusion zones were not marked during night shifts; a compliance order requires "
     "barriers and a lifting plan within thirty days."),
    (2, "Inspectorate v Dravos Pipeline Services", INSPECTORATE, S, "2024-07-09",
     Outcome.COMPLIANCE_ORDER, 210_000, ["ISC reg. 31", "ISC reg. 12"], WYNMOOR,
     "Confined space entry without a gas test or standby attendant; order to suspend entries "
     "until permits and rescue equipment are in place."),
    (3, "Osmere Offshore Works v Inspectorate", TRIBUNAL, S, "2024-10-23", Outcome.DISMISSED,
     48_000, ["ISC reg. 44"], CALLOWAY,
     "Appeal against a prohibition notice dismissed: the scaffold inspection register had "
     "gaps of several weeks."),
    (4, "Yarrowby Marine Fabrication v Inspectorate", TRIBUNAL, S, "2025-02-11", Outcome.UPHELD,
     132_500, ["ISC reg. 12", "ISC reg. 67"], CALLOWAY,
     "Appeal upheld: the notice named the wrong duty holder for the lock-out procedure and "
     "is set aside."),
    (5, "Inspectorate v Sablewood Dredging", INSPECTORATE, S, "2025-06-03",
     Outcome.SETTLED_WITH_COSTS, 90_250, ["ISC reg. 31", "ISC reg. 67"], ROOKE,
     "Working at height without edge protection on a barge; enforcement settled with an "
     "undertaking and the operator pays the investigation costs."),
    (6, "Inspectorate v Vantry Harbour Cranes", INSPECTORATE, S, "2025-09-17",
     Outcome.COMPLIANCE_ORDER, 305_000, ["ISC reg. 31", "ISC reg. 44", "ISC reg. 12"], WYNMOOR,
     "Repeated overload alarms on a gantry crane were silenced; order to recalibrate load "
     "cells and retrain operators."),
    (7, "Conformity Office v Lumestra Conveyors", OFFICE, M, "2024-04-18",
     Outcome.COMPLIANCE_ORDER, 58_400, ["MCR r. 8", "MCR r. 19"], WYNMOOR,
     "Conveyor nip points had no fixed guards and the emergency stop did not latch; order to "
     "retrofit guarding before restart."),
    (8, "Kilnwarth Presses v Conformity Office", OFFICE, M, "2024-12-05", Outcome.DISMISSED,
     27_900, ["MCR r. 8"], ROOKE,
     "Objection to a conformity refusal dismissed: the light curtain response time exceeded "
     "the declared stopping distance."),
    (9, "Conformity Office v Zephran Robotics", OFFICE, M, "2025-05-22", Outcome.UPHELD, 164_000,
     ["MCR r. 19", "MCR r. 26"], ROOKE,
     "Robot cell interlock could be bypassed with a spare key; the withdrawal of the "
     "conformity mark is upheld."),
    (10, "Conformity Office v Brindlow Packaging Lines", OFFICE, M, "2025-11-06",
     Outcome.SETTLED_WITH_COSTS, 41_750, ["MCR r. 8", "MCR r. 26"], WYNMOOR,
     "Missing technical file for a modified wrapping machine; settled once the file was "
     "rebuilt, with costs paid by the operator."),
)
