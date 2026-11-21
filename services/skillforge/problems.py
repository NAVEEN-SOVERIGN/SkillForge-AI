
from dataclasses import dataclass

PROBLEM_VERSION = "2"

@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    difficulty: str
    topic: str
    story: str
    contract: str
    examples: tuple
    hidden: tuple
    walkthrough: str

    def public(self):
        return {
            "id": self.id, "title": self.title, "difficulty": self.difficulty, "story": self.story,
            "contract": self.contract, "examples": [{"input": value, "output": expected}
                                                   for value, expected in self.examples],
            "languages": ["python", "javascript"], "version": PROBLEM_VERSION,
        }


PROBLEMS = {problem.id: problem for problem in (
    Problem("warehouse-reconciliation", "Warehouse reconciliation", "Foundations", "Hash maps",
            "A warehouse receives shipment and sale events for each SKU. Summarize the final stock movement.",
            "Input is an array of [sku, change] pairs. Return an object mapping each SKU to its net change. "
            "Include SKUs with zero net change. There are at most 20,000 events.",
            (([["tea", 3], ["rice", 4], ["tea", -1]], {"tea": 2, "rice": 4}),),
            (([], {}), ([["x", 2], ["x", -2]], {"x": 0}), ([["tea", -1]] * 9000, {"tea": -9000})),
            "Accumulate into a hash map keyed by SKU. Add each change once, for O(n) time."),
    Problem("earliest-duplicate", "Duplicate invoice alerts", "Foundations", "Hash sets",
            "An invoice stream sometimes delivers the same identifier twice. Report the first repeated identifier.",
            "Input is an array of up to 50,000 strings. Return the first string encountered a second time, or null.",
            ((["a7", "b4", "c9", "b4", "a7"], "b4"),),
            (([], None), (["x", "x"], "x"), (list(map(str, range(12000))) + ["3"], "3")),
            "Keep a set of seen identifiers and return on the first repeated item. Expected time is O(n)."),
    Problem("support-coverage", "Peak support coverage", "Intermediate", "Sweep line",
            "A support manager wants to know the largest number of agents on duty at once.",
            "Input is an array of [start, end] integer intervals with start < end. Intervals are half-open. "
            "Return the largest count of overlapping shifts. There are up to 20,000 shifts.",
            (([[0, 5], [1, 6], [5, 7]], 2),),
            (([], 0), ([[1, 2], [2, 3]], 1), ([[0, n] for n in range(1, 5000)], 4999)),
            "Make a start and end event per shift. Sort by time, applying ends before starts at equal times."),
    Problem("room-booking", "Combine room reservations", "Intermediate", "Sorting and intervals",
            "A room display needs a compact schedule for reservations that overlap or touch.",
            "Input is an array of valid [start, end] pairs. Return sorted merged intervals, merging touching endpoints. "
            "There are up to 20,000 reservations.",
            (([[5, 8], [1, 3], [3, 5], [9, 10]], [[1, 8], [9, 10]]),),
            (([], []), ([[0, 8], [3, 5], [8, 9]], [[0, 9]]), ([[i, i + 2] for i in range(4000)], [[0, 4001]])),
            "Sort by start and compare each interval with the current merged interval."),
    Problem("load-monitor", "Busiest rolling window", "Foundations", "Sliding window",
            "A monitoring system summarizes the busiest fixed-length interval in its request log.",
            "Input is {requests: integer[], window: integer}. Return the largest sum across contiguous "
            "segments of exactly window length. Window is at least 1 and fits the array, which has up to 50,000 items.",
            (({"requests": [1, 8, 3, 7, 2], "window": 2}, 11),),
            (({"requests": [3], "window": 1}, 3), ({"requests": [1, 2], "window": 2}, 3),
             ({"requests": [3] * 30000, "window": 10000}, 30000)),
            "Track the first window sum, then add the entering item and subtract the leaving item at each shift."),
    Problem("shipment-capacity", "Find a van that fits", "Foundations", "Binary search",
            "A dispatch center has sorted the available vans by capacity. Find the smallest suitable slot for an order.",
            "Input is {capacities: sorted integer[], load: integer}. Return the zero-based index of the first value "
            "at least load, or -1. There are up to 50,000 vans.",
            (({"capacities": [3, 5, 5, 9], "load": 5}, 1),),
            (({"capacities": [], "load": 1}, -1), ({"capacities": [1], "load": 2}, -1),
             ({"capacities": list(range(20000)), "load": 10000}, 10000)),
            "Use lower-bound binary search and check that the resulting index is within bounds."),
    Problem("helpdesk-priority", "Helpdesk escalation queue", "Intermediate", "Priority queues",
            "New support tickets arrive throughout the day. Resolve events should take the highest priority waiting ticket.",
            "Input has operations ['add', id, priority] or ['resolve']. Larger priorities go first. Equal "
            "priorities use arrival order. Return an array of resolved IDs with null for an empty resolve. Up to 20,000 events.",
            (([["add", "A", 2], ["add", "B", 7], ["resolve"], ["resolve"]], ["B", "A"]),),
            (([["resolve"]], [None]), ([["add", "A", 2], ["add", "B", 2], ["resolve"]], ["A"]),
             ([["add", str(i), i] for i in range(3500)] + [["resolve"]] * 3500,
              [str(i) for i in reversed(range(3500))])),
            "Use a heap with keys of negative priority and arrival index to preserve stable ordering."),
    Problem("office-network", "Office network handoffs", "Intermediate", "Breadth-first search",
            "A helpdesk is routing messages between connected offices. Find the shortest number of handoffs.",
            "Input is {links: [string,string][], start: string, end: string}. Links are undirected. Return the "
            "fewest edges between start and end, or -1. At most 20,000 links.",
            (({"links": [["a", "b"], ["b", "c"], ["a", "d"]], "start": "a", "end": "c"}, 2),),
            (({"links": [], "start": "a", "end": "a"}, 0), ({"links": [], "start": "a", "end": "b"}, -1),
             ({"links": [[str(i), str(i + 1)] for i in range(3500)], "start": "0", "end": "3500"}, 3500)),
            "Build an adjacency list and use breadth-first search with a visited set."),
    Problem("course-launch", "Course release prerequisites", "Intermediate", "Topological ordering",
            "A platform schedules courses once all prerequisite courses are ready. Decide whether the full schedule is possible.",
            "Input is {count: integer, requirements: [integer,integer][]}. Each [course, prerequisite] uses "
            "zero-based course IDs. Return true if all courses can be scheduled, otherwise false. Up to 20,000 requirements.",
            (({"count": 3, "requirements": [[1, 0], [2, 1]]}, True),),
            (({"count": 1, "requirements": [[0, 0]]}, False), ({"count": 0, "requirements": []}, True),
             ({"count": 4001, "requirements": [[i + 1, i] for i in range(4000)] + [[0, 4000]]}, False)),
            "Track prerequisite counts and repeatedly process the nodes with zero remaining dependencies."),
    Problem("voucher-change", "Fewest voucher codes", "Advanced", "Dynamic programming",
            "A store composes a credit using reusable voucher denominations. Find the fewest codes needed.",
            "Input is {values: positive integer[], total: integer}. Return the minimum number of codes for "
            "an exact total or -1 if impossible. Denominations can repeat. Total is between 0 and 20,000.",
            (({"values": [1, 3, 4], "total": 6}, 2),),
            (({"values": [2], "total": 3}, -1), ({"values": [], "total": 0}, 0),
             ({"values": [1, 5, 25], "total": 19999}, 807)),
            "Fill a table by subtotal, taking the minimum of one plus the result for each smaller reachable subtotal."),
    Problem("campaign-scheduling", "Choose non-overlapping campaigns", "Advanced", "Weighted interval scheduling",
            "A storefront can feature only one campaign at a time. Find the most valuable compatible set.",
            "Input is up to 20,000 [start, end, value] triples with start < end and value >= 0. "
            "Touching boundaries are compatible. Return the maximum total value.",
            (([[0, 3, 5], [3, 7, 6], [1, 6, 12]], 12),),
            (([], 0), ([[1, 2, 3], [2, 3, 4]], 7),
             ([[i, i + 1, 1] for i in range(4500)] + [[0, 4500, 2000]], 4500)),
            "Sort by end time, find each compatible predecessor by binary search, and use a running best-value table."),
    Problem("customer-retry", "Consolidate retry batches", "Intermediate", "Prefix sums",
            "A job queue stores work by customer segment. The manager requests totals for contiguous ranges.",
            "Input is {jobs: integer[], queries: [integer,integer][]}. A query [left,right] is zero-based "
            "and inclusive. Return one total per query. Up to 40,000 jobs and queries.",
            (({"jobs": [4, 7, 1, 2], "queries": [[0, 1], [1, 3]]}, [11, 10]),),
            (({"jobs": [], "queries": []}, []), ({"jobs": [8], "queries": [[0, 0]]}, [8]),
             ({"jobs": [2] * 10000, "queries": [[0, 9999]] * 4000}, [20000] * 4000)),
            "Build a prefix sum with an initial zero. Answer each range with one subtraction."),
)}

FUNCTIONAL_CASES = {
    "warehouse-reconciliation": ([["lime", 3], ["rice", -2], ["lime", 1]], {"lime": 4, "rice": -2}),
    "earliest-duplicate": (["a", "b", "c"], None),
    "support-coverage": ([[1, 4], [2, 3], [2, 4], [3, 5]], 3),
    "room-booking": ([[8, 9], [2, 4], [1, 2], [5, 6]], [[1, 4], [5, 6], [8, 9]]),
    "load-monitor": ({"requests": [4, 0, 8, 5], "window": 2}, 13),
    "shipment-capacity": ({"capacities": [1, 4, 6, 10], "load": 5}, 2),
    "helpdesk-priority": ([["add", "x", 5], ["resolve"], ["add", "y", 1], ["resolve"]], ["x", "y"]),
    "office-network": ({"links": [["r", "s"], ["s", "t"], ["c", "z"]], "start": "t", "end": "r"}, 2),
    "course-launch": ({"count": 4, "requirements": [[1, 0], [2, 3]]}, True),
    "voucher-change": ({"values": [3, 7, 11], "total": 14}, 2),
    "campaign-scheduling": ([[0, 4, 6], [4, 7, 4], [1, 7, 8]], 10),
    "customer-retry": ({"jobs": [4, -2, 8], "queries": [[0, 2], [2, 2], [0, 0]]}, [10, 8, 4]),
}
