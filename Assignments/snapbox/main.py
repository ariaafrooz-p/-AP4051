"""Text interface following the Quera statement (problem 106799).

Contains no business logic: it parses a line, calls DeliverySystem and
formats the result.
"""
import re
import sys

from delivery_system import DeliverySystem

_POS_RE = re.compile(r"\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)")


def _none_or(value):
    return "None" if value is None else str(value)


def _join(items):
    return " ".join(items) if items else "None"


def _fmt_pos(p):
    return f"({p[0]}, {p[1]})"


def handle(system, line):
    """Execute one command line and return the output text ('' for END/blank)."""
    positions = [(int(x), int(y)) for x, y in _POS_RE.findall(line)]
    tokens = _POS_RE.sub("P", line).split()
    if not tokens:
        return ""
    cmd, a = tokens[0], tokens[1:]

    if cmd == "ADD-DRIVER":            # ADD-DRIVER user POS CATEGORY
        ok = system.add_driver(a[0], positions[0], a[2])
        return "user added successfully" if ok else "user previously added"

    if cmd == "CREATE-ORDER":          # CREATE-ORDER CATEGORY POS POS
        r = system.create_order(a[0], positions[0], positions[1])
        return "invalid order" if r is None else str(r)

    if cmd == "ASSIGN-NEXT-ORDER":     # ASSIGN-NEXT-ORDER user
        try:
            r = system.assign_next_order(a[0])
        except KeyError:
            return "invalid driver name"
        except RuntimeError:
            return "driver is already busy"
        return "there is no order right now" if r is None else f"{r} assigned to {a[0]}"

    if cmd == "GET-DRIVER":
        r = system.get_driver(a[0])
        if r is None:
            return "invalid driver name"
        return f"{r[0]} {_fmt_pos(r[1])} {int(r[2])}"

    if cmd == "ORDER-UPDATE":          # ORDER-UPDATE STATUS user order_id
        status, user, oid = a[0], a[1], int(a[2])
        if system.get_driver(user) is None:
            return "invalid driver name"
        if system.get_current_order_id(user) != oid:
            return "wrong order-id"
        try:
            ok = system.update_order_status(user, oid, status)
        except ValueError:
            ok = False
        return "status changed successfully" if ok else "invalid status"

    if cmd == "GET-ORDER":
        r = system.get_order(int(a[0]))
        if r is None:
            return "invalid order"
        return f"{r[0]} {_none_or(r[1])} {int(r[2])}"

    if cmd == "GET-ORDER-LIST":
        return _join([str(i) for i in system.get_order_list(a[0])])

    if cmd == "GET-DRIVER-LIST":
        return _join(system.get_driver_list(a[0]))

    if cmd == "GET-NEAR-DRIVER":       # GET-NEAR-DRIVER POS COUNT
        return _join(system.get_near_drivers(positions[0], int(a[1])))

    if cmd == "GET-CNT-ORDER":         # GET-CNT-ORDER POS DISTANCE START|FINISH
        return str(system.count_orders(positions[0], int(a[1]), a[2]))

    if cmd == "GET-NEAREST-PENDING-ORDER":
        return _none_or(system.get_nearest_pending_order(positions[0]))

    if cmd == "GET-COMPANY":
        return str(int(system.get_company_credit()))

    return ""  # END or unknown


def main(stream=None):
    stream = stream or sys.stdin
    system = DeliverySystem()
    for line in stream:
        if line.strip() == "END":
            break
        out = handle(system, line)
        if out:
            print(out)


if __name__ == "__main__":
    main()
