"""
Graph utility functions for cycle detection in directed graphs.

This module provides utilities for working with graph structures, particularly
for detecting cycles in directed acyclic graphs (DAGs).

Functions
--------
check_cycle
    Checks the given DAG for cycles and returns nodes that are part of a cycle.
"""

import collections


def check_cycle(node_successors: dict[str, list[str]]) -> tuple[bool, list[str]]:
    """
    Checks the given DAG for cycles and returns nodes that are part of a cycle.

    This function implements a topological sorting algorithm to detect cycles
    in a directed graph. It works by tracking the in-degree (number of incoming edges)
    for each node and progressively removing nodes with zero in-degree.
    If any nodes remain with non-zero in-degree after the process, a cycle exists.

    Parameters
    ----------
    node_successors : dict[str, list[str]]
        A dictionary where keys are node names and values are lists of successor node names.
        This represents the graph structure as an adjacency list.

    Returns
    -------
    tuple[bool, list[str] or None]
        A tuple containing:
        - bool: True if a cycle was detected, False otherwise
        - list[str] or None: If a cycle exists, a list of nodes that are part of the cycle;
          otherwise None.

    Examples
    --------
    >>> # Graph with no cycle
    >>> no_cycle = {'A': ['B', 'C'], 'B': ['D'], 'C': ['D'], 'D': []}
    >>> check_cycle(no_cycle)
    (False, None)

    >>> # Graph with a cycle
    >>> has_cycle = {'A': ['B'], 'B': ['C'], 'C': ['A']}
    >>> check_cycle(has_cycle)
    (True, ['A', 'B', 'C'])
    """

    # Step 1: Calculate in-degree (number of incoming edges) for each node
    in_degree = dict.fromkeys(node_successors.keys(), 0)

    for successors in node_successors.values():
        for successor in successors:
            in_degree[successor] += 1

    # Step 2: Initialize a queue with all nodes that have in-degree 0
    queue = collections.deque([node for node in node_successors.keys() if in_degree[node] == 0])

    # Number of processed nodes
    processed_count = 0

    # Step 3: Process nodes with in-degree 0
    while queue:
        current_node = queue.popleft()
        processed_count += 1

        # Decrease the in-degree of each successor by 1
        for successor in node_successors[current_node]:
            in_degree[successor] -= 1
            # If in-degree becomes 0, add it to the queue
            if in_degree[successor] == 0:
                queue.append(successor)

    # Step 4: Identify the faulty nodes (those still with in-degree > 0)
    faulty_nodes = [node for node in node_successors.keys() if in_degree[node] > 0]

    # If there are faulty nodes, there's a cycle
    if faulty_nodes:
        return True, faulty_nodes
    else:
        return False, None
