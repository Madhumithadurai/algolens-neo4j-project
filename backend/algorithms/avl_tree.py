"""AVL tree: a self-balancing binary search tree.

Search, insert: O(log n) time. The tree itself needs O(n) memory.
"""


class AVLNode:
    __slots__ = ("key", "left", "right", "height")

    def __init__(self, key):
        self.key = key
        self.left = None
        self.right = None
        self.height = 1


def _h(node):
    return node.height if node else 0


def _update(node):
    node.height = 1 + max(_h(node.left), _h(node.right))


def _balance(node):
    return _h(node.left) - _h(node.right)


class AVLTree:
    def __init__(self, record_steps=False, snapshots=False, max_steps=3000):
        """
        record_steps: keep a log of insertions and rotations.
        snapshots:    also store a copy of the whole tree after every insertion
                      (only sensible for small inputs). Without snapshots, only
                      insertions that caused a rotation are logged.
        """
        self.root = None
        self.size = 0
        self.rotations = 0
        self.record = record_steps
        self.snapshots = snapshots
        self.max_steps = max_steps
        self.steps = []
        self.truncated = False
        self._pending = []

    # ---- rotations -----------------------------------------------------------
    @staticmethod
    def _rotate_right(y):
        x = y.left
        y.left = x.right
        x.right = y
        _update(y)
        _update(x)
        return x

    @staticmethod
    def _rotate_left(x):
        y = x.right
        x.right = y.left
        y.left = x
        _update(x)
        _update(y)
        return y

    # ---- insertion -----------------------------------------------------------
    def insert(self, key):
        self._pending = []
        flag = [False]
        self.root = self._insert(self.root, key, flag)
        inserted = flag[0]
        if inserted:
            self.size += 1
        if self.record and (self.snapshots or self._pending):
            if len(self.steps) < self.max_steps:
                step = {"type": "insert", "key": key, "duplicate": not inserted,
                        "rotations": self._pending}
                if self.snapshots:
                    step["tree"] = self.to_dict()
                self.steps.append(step)
            else:
                self.truncated = True
        return inserted

    def _insert(self, node, key, flag):
        if node is None:
            flag[0] = True
            return AVLNode(key)
        if key < node.key:
            node.left = self._insert(node.left, key, flag)
        elif key > node.key:
            node.right = self._insert(node.right, key, flag)
        else:
            return node  # duplicate keys are ignored

        _update(node)
        b = _balance(node)
        if b > 1:
            if key < node.left.key:
                kind, new_root = "LL", self._rotate_right(node)
                self.rotations += 1
            else:
                node.left = self._rotate_left(node.left)
                kind, new_root = "LR", self._rotate_right(node)
                self.rotations += 2
        elif b < -1:
            if key > node.right.key:
                kind, new_root = "RR", self._rotate_left(node)
                self.rotations += 1
            else:
                node.right = self._rotate_right(node.right)
                kind, new_root = "RL", self._rotate_left(node)
                self.rotations += 2
        else:
            return node
        if self.record:
            self._pending.append({"kind": kind, "pivot": node.key, "newRoot": new_root.key})
        return new_root

    # ---- search --------------------------------------------------------------
    def search(self, key):
        """Search and return the visited path for visualisation."""
        path = []
        node = self.root
        comparisons = 0
        while node is not None:
            comparisons += 1
            if key == node.key:
                path.append({"key": node.key, "action": "found"})
                return {"found": True, "comparisons": comparisons, "path": path}
            if key < node.key:
                path.append({"key": node.key, "action": "go-left"})
                node = node.left
            else:
                path.append({"key": node.key, "action": "go-right"})
                node = node.right
        return {"found": False, "comparisons": comparisons, "path": path}

    def contains(self, key):
        """Search without recording; used for timing."""
        node = self.root
        while node is not None:
            k = node.key
            if key == k:
                return True
            node = node.left if key < k else node.right
        return False

    # ---- inspection ----------------------------------------------------------
    def height(self):
        return _h(self.root)

    def to_dict(self):
        def walk(n):
            if n is None:
                return None
            return {"key": n.key, "height": n.height, "balance": _balance(n),
                    "left": walk(n.left), "right": walk(n.right)}
        return walk(self.root)

    def is_valid(self):
        """True if BST ordering, stored heights and AVL balance all hold."""
        def check(n, lo, hi):
            if n is None:
                return True, 0
            if (lo is not None and n.key <= lo) or (hi is not None and n.key >= hi):
                return False, 0
            ok_l, hl = check(n.left, lo, n.key)
            ok_r, hr = check(n.right, n.key, hi)
            h = 1 + max(hl, hr)
            return ok_l and ok_r and abs(hl - hr) <= 1 and n.height == h, h
        return check(self.root, None, None)[0]

    def inorder(self):
        out, stack, node = [], [], self.root
        while stack or node:
            while node:
                stack.append(node)
                node = node.left
            node = stack.pop()
            out.append(node.key)
            node = node.right
        return out
