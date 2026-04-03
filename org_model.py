"""
Organization model — defines users, roles, hierarchy, and access rules.

Hierarchy:  Director → Manager → Employee
Visibility: "shared" (org-wide) or "private" (owner's personal space)

Access rules:
  - Employee:  shared docs + own private docs
  - Manager:   shared docs + own private + direct reports' private docs
  - Director:  everything
"""

from dataclasses import dataclass, field

ROLES = ("director", "manager", "employee")


@dataclass
class User:
    name: str
    role: str          # one of ROLES
    reports_to: str | None = None  # name of their manager (None for director)

    @property
    def display(self) -> str:
        return f"{self.name} ({self.role.title()})"


# ── The org chart ────────────────────────────────────────────────────
# Edit this to change the demo organization.

ORG: dict[str, User] = {}

def _register(*users):
    for u in users:
        ORG[u.name] = u

_register(
    User(name="Arjun",   role="director"),
    User(name="Meera",   role="manager",  reports_to="Arjun"),
    User(name="Priya",   role="employee", reports_to="Meera"),
    User(name="Rahul",   role="employee", reports_to="Meera"),
)


def get_user(name: str) -> User | None:
    return ORG.get(name)


def list_users() -> list[User]:
    role_order = {r: i for i, r in enumerate(ROLES)}
    return sorted(ORG.values(), key=lambda u: (role_order.get(u.role, 99), u.name))


def direct_reports(manager_name: str) -> list[str]:
    """Return names of users who report to *manager_name*."""
    return [u.name for u in ORG.values() if u.reports_to == manager_name]


def all_subordinates(name: str) -> list[str]:
    """Recursively collect all subordinates (reports, their reports, etc.)."""
    subs = []
    for report in direct_reports(name):
        subs.append(report)
        subs.extend(all_subordinates(report))
    return subs


def visible_owners(user: User) -> set[str | None]:
    """
    Return the set of 'owner' values this user is allowed to see.

    - None means "shared / org-wide" — everyone can see those.
    - A name string means "private to that person".

    Director  → {None, everyone}
    Manager   → {None, self, direct reports + their subtrees}
    Employee  → {None, self}
    """
    allowed: set[str | None] = {None, user.name}  # shared + own

    if user.role == "director":
        allowed.update(u.name for u in ORG.values())
    elif user.role == "manager":
        allowed.update(all_subordinates(user.name))

    return allowed
