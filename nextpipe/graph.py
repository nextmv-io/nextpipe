import collections


def check_cycle(node_successors: dict[str, list[str]]) -> tuple[bool, list[str]]:
    """
    Checks the given DAG for cycles and returns nodes that are part of a cycle.

    :param node_successors: A dictionary where keys are node names and values are lists of successor node names.
    :return: A tuple (has_cycle, faulty_nodes) where has_cycle is a boolean indicating whether a cycle was found and
    faulty_nodes is a list of nodes that are part of the cycle.
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
