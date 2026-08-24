"""Roles as first-class entities -- layer 4 extension, Tier 5 (ladder T5.1-T5.3).

Design doc: docs/design/tier-5-roles-and-vacancy.md (S1/S2). A Role is a
different axis of state from chronicle.social's four kinds (relationships,
grudges, obligations, reputation): an office that outlives any one holder,
not a fact about one NPC or one pair -- hence its own module, the same
one-concern-per-module discipline claims.py/social.py/schedule.py/events.py
already follow.

T5.3's "no orphaned references" (design doc Decision S2, ruled O1) holds by
construction rather than by retrofitting: Role-owned state (holder, duties,
vacancy) lives ONLY on the Role, keyed by role_id, and is never mirrored
onto the holder's own records. RoleStore.holder_of() is the one place a
caller asks "who currently holds this role" -- nothing else in this
codebase stores an npc id as a proxy for a role, and nothing here should
start.
"""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Duty:
    """One duty a role's holder performs; its lapse consequence is a status_changed event (design doc S4).

    lapse_status_kind names the status_changed record's status_kind
    field emitted when this duty lapses (schema §3:97) -- e.g.
    "duty_lapsed". A plain string, not a payload: the effect a lapsed
    duty has on the world is scenario/fixture-defined (the same
    caller-supplies-context discipline as claim_privacy/
    mutation_candidates elsewhere), not something this module models.
    """

    name: str
    lapse_status_kind: str


@dataclass(frozen=True)
class Role:
    """A first-class office (design doc S1): id, institution, duties, and the current holder.

    holder_id is None exactly when vacant; vacated_at is the gamets of
    the most recent vacancy (None if never vacated). institution_id is
    the same basis_id vocabulary chronicle.social.Relationship's
    "faction"/"shared_employer" edges already use (e.g.
    "whiterun_court") -- succession (Tier 5 L-J) ranks candidates by
    their relationship strength to this same institution_id.
    """

    id: str
    title: str
    institution_id: str
    duties: tuple[Duty, ...]
    holder_id: str | None
    vacated_at: float | None


class RoleStore:
    """The queryable role store. Mirrors SocialStateStore's shape: pure constructor + store + replace-mutations.

    There is deliberately no bulk "all roles" query beyond roles_held_by
    (a holder-scoped reverse index) -- callers ask about one role or one
    NPC's roles, never sweep the whole store, the same sparse-access
    discipline chronicle.social documents for its own indices.
    """

    def __init__(self) -> None:
        self._roles: dict[str, Role] = {}
        self._roles_by_holder: dict[str, set[str]] = {}

    def install(self, role: Role) -> Role:
        """First-time registration. Raises if role.id already exists -- use vacate() to mutate it, not a second install()."""
        if role.id in self._roles:
            raise ValueError(f"role {role.id!r} already installed -- use vacate() to mutate it, not a second install()")
        self._roles[role.id] = role
        if role.holder_id is not None:
            self._roles_by_holder.setdefault(role.holder_id, set()).add(role.id)
        return role

    def role(self, role_id: str) -> Role | None:
        return self._roles.get(role_id)

    def holder_of(self, role_id: str) -> str | None:
        """The current holder, or None if vacant or unknown. The one place to ask this -- never mirror it elsewhere."""
        role = self._roles.get(role_id)
        return role.holder_id if role is not None else None

    def roles_held_by(self, npc_id: str) -> tuple[Role, ...]:
        ids = self._roles_by_holder.get(npc_id, ())
        return tuple(self._roles[i] for i in ids)

    def vacate(self, role_id: str, *, gamets: float) -> Role:
        """Clear a role's holder (design doc S3: vacancy is objective, derived state -- no trace record of its own)."""
        role = self._roles[role_id]
        if role.holder_id is not None:
            self._roles_by_holder[role.holder_id].discard(role_id)
        updated = replace(role, holder_id=None, vacated_at=gamets)
        self._roles[role_id] = updated
        return updated
