from typing import Set
from pm4py.objects.dcr.extended.semantics import ExtendedSemantics

class HierarchicalSemantics(ExtendedSemantics):
    @classmethod
    def enabled(cls, graph) -> Set[str]:
        print("\n[DEBUG] -- Calculating Enabled Events --")
        print(f"Graph State - Included: {graph.marking.included}")
        print(f"Graph State - Executed: {graph.marking.executed}")
        print(f"Graph State - Pending: {graph.marking.pending}")

        # Start from all included events
        res = set(graph.marking.included)

        # Conditio
        for e in set(graph.conditions.keys()).intersection(res):
            unmet = graph.conditions[e].intersection(
                graph.marking.included.difference(graph.marking.executed)
            )
            if unmet:
                print(f"[DEBUG] Event {e} is NOT enabled; unmet condition(s): {unmet}")
                res.discard(e)

        # Milestone
        for e in set(graph.milestones.keys()).intersection(res):
            blocked_by = graph.milestones[e].intersection(
                graph.marking.included.intersection(graph.marking.pending)
            )
            if blocked_by:
                print(f"[DEBUG] Event {e} is NOT enabled; blocked by milestone(s): {blocked_by}")
                res.discard(e)

        # Discard events that are pending themselves
        for e in graph.marking.pending:
            if e in res:
                print(f"[DEBUG] Event {e} is NOT enabled (it is itself pending).")
                res.discard(e)

        # If a nested group name is in graph.conditions, discard events
        for group_name in set(graph.conditions.keys()).intersection(graph.nestedgroups):
            print(f"[DEBUG] Group '{group_name}' appears as a 'condition' key. Discarding its events.")
            for evt_in_group in graph.nestedgroups[group_name]:
                if evt_in_group in res:
                    print(f"[DEBUG] Discarding event {evt_in_group} because its group '{group_name}' is a condition.")
                    res.discard(evt_in_group)

        # Debug each nested group
        for grp, members in graph.nestedgroups.items():
            any_pending = any(evt in graph.marking.pending for evt in members)
            all_executed = all(evt in graph.marking.executed for evt in members)
            print(f"[DEBUG] Checking nested group '{grp}' => {members}")
            print(f"        - Any pending in group? {any_pending}")
            print(f"        - All executed in group? {all_executed}")

        print(f"[DEBUG] -- Enabled Events: {res}")
        return res

    @classmethod
    def execute(cls, graph, event):
        print(f"\n[DEBUG] -- Executing Event: {event} --")
        print(f"State Before Execution - Included: {graph.marking.included}")
        print(f"State Before Execution - Executed: {graph.marking.executed}")
        print(f"State Before Execution - Pending: {graph.marking.pending}")

        # If event not included, try group inclusion
        if event not in graph.marking.included:
            print(f"[DEBUG] Event {event} is not included; checking nestedgroups_map.")
            if hasattr(graph, "nestedgroups_map") and event in graph.nestedgroups_map:
                group_name = graph.nestedgroups_map[event]
                if group_name in graph.nestedgroups:
                    print(f"[DEBUG] Including entire group '{group_name}' for event {event}.")
                    for mem in graph.nestedgroups[group_name]:
                        graph.marking.included.add(mem)
            if event not in graph.marking.included:
                raise ValueError(f"Event {event} cannot be executed because it is not included.")

        # event marked as executed
        graph.marking.executed.add(event)

        # Remove from pending if present
        if event in graph.marking.pending:
            print(f"[DEBUG] Resolving pending for event {event}.")
            graph.marking.pending.discard(event)

        # Responses add them to pending
        if event in graph.responses:
            for e_prime in graph.responses[event]:
                print(f"[DEBUG] Adding {e_prime} to pending (response from {event}).")
                graph.marking.pending.add(e_prime)

        # Handle includes
        if event in graph.includes:
            for e_prime in graph.includes[event]:
                if e_prime not in graph.marking.included:
                    print(f"[DEBUG] Including {e_prime} (include relation from {event}).")
                    graph.marking.included.add(e_prime)

        # Handle excludes
        if event in graph.excludes:
            for e_prime in graph.excludes[event]:
                if e_prime in graph.marking.included:
                    print(f"[DEBUG] Excluding {e_prime} (exclude relation from {event}).")
                    graph.marking.included.discard(e_prime)

        # Debug group
        if hasattr(graph, "nestedgroups_map") and event in graph.nestedgroups_map:
            grp_name = graph.nestedgroups_map[event]
            siblings = graph.nestedgroups.get(grp_name, set())
            print(f"[DEBUG] Event {event} belongs to nested group '{grp_name}'. Siblings: {siblings}")

        print(f"[DEBUG] -- State After Execution of {event} --")
        print(f"State After Execution - Included: {graph.marking.included}")
        print(f"State After Execution - Executed: {graph.marking.executed}")
        print(f"State After Execution - Pending: {graph.marking.pending}")

        return graph

    @classmethod
    def is_accepting(cls, graph) -> bool:
        """
        'is_accepting' method to avoid AttributeError in tests.
        By default, we say the graph is 'NOT accepting' if any included event is pending.
        """
        pend_incl = graph.marking.pending.intersection(graph.marking.included)
        if pend_incl:
            print(f"[DEBUG] Graph is NOT accepting. Pending included events: {pend_incl}")
            return False
        print("[DEBUG] Graph is accepting.")
        return True
