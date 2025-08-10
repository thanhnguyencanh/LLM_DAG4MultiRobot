# coop_planner.py
import sys
import uuid
from typing import Dict, Set, Tuple, List, Optional
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QTextEdit, QLineEdit, QPushButton, QGraphicsView, QGraphicsScene, QGraphicsRectItem,
    QGraphicsTextItem, QLabel
)
from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF
from PyQt5.QtGui import QColor, QBrush, QPen

# ------------------------------
# Graph model
# ------------------------------
class ActionNode:
    def __init__(self, label: str, actor: str, duration: float = 3.0, ephemeral: bool = False):
        self.id = str(uuid.uuid4())
        self.label = label
        assert actor in ("human", "robot", "handover")
        self.actor = actor
        self.duration = duration
        self.ephemeral = ephemeral
        self.status = "Pending"  # Pending / In Progress / Done / Failed

    def __repr__(self):
        return f"Node({self.label[:12]}...,{self.actor},{self.status})"


class GraphPlan:
    def __init__(self):
        self.nodes: Dict[str, ActionNode] = {}
        self.edges: Set[Tuple[str, str]] = set()  # directed edges (from,to)

    # node helpers
    def add_node(self, node: ActionNode):
        self.nodes[node.id] = node
        return node.id

    def remove_node(self, node_id: str):
        if node_id not in self.nodes:
            return
        # remove edges incident
        self.edges = {e for e in self.edges if e[0] != node_id and e[1] != node_id}
        del self.nodes[node_id]

    def add_edge(self, from_id: str, to_id: str):
        if from_id == to_id:
            return False
        self.edges.add((from_id, to_id))
        if self.has_cycle():
            # revert
            self.edges.remove((from_id, to_id))
            return False
        return True

    def remove_edge(self, from_id: str, to_id: str):
        if (from_id, to_id) in self.edges:
            self.edges.remove((from_id, to_id))

    def predecessors(self, node_id: str):
        return [a for (a, b) in self.edges if b == node_id]

    def successors(self, node_id: str):
        return [b for (a, b) in self.edges if a == node_id]

    def has_cycle(self):
        # simple DFS for cycle detection
        visited = {}
        def dfs(n):
            if n in visited:
                return visited[n] == 1
            visited[n] = 1
            for s in self.successors(n):
                if dfs(s):
                    return True
            visited[n] = 2
            return False
        for nid in list(self.nodes.keys()):
            if nid not in visited:
                if dfs(nid):
                    return True
        return False

    def find_by_label(self, keyword: str) -> Optional[str]:
        kw = keyword.lower()
        for nid, node in self.nodes.items():
            if kw in node.label.lower():
                return nid
        return None

    def topo_ready(self) -> List[str]:
        # nodes pending whose predecessors are done
        ready = []
        for nid, n in self.nodes.items():
            if n.status != "Pending":
                continue
            preds = self.predecessors(nid)
            if all(self.nodes[p].status == "Done" for p in preds):
                ready.append(nid)
        return ready

# ------------------------------
# GUI / App
# ------------------------------
class TaskTable(QGroupBox):
    def __init__(self, title):
        super().__init__(title)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Task", "Status"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Fixed)
        self.table.setColumnWidth(1, 100)
        self.table.setAlternatingRowColors(True)
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.setLayout(layout)

    def clear(self):
        self.table.setRowCount(0)

    def add_row(self, task: str, status: str):
        r = self.table.rowCount()
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem(task))
        item = QTableWidgetItem(status)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(self.status_color(status))
        self.table.setItem(r, 1, item)

    def update_status_row(self, row: int, status: str):
        item = QTableWidgetItem(status)
        item.setTextAlignment(Qt.AlignCenter)
        item.setBackground(self.status_color(status))
        self.table.setItem(row, 1, item)

    def find_row_by_text(self, text_part: str):
        for r in range(self.table.rowCount()):
            if text_part.lower() in self.table.item(r, 0).text().lower():
                return r
        return None

    @staticmethod
    def status_color(status: str):
        if status == "Pending":
            return QBrush(QColor("#dddddd"))
        if status == "In Progress":
            return QBrush(QColor("#ffdd88"))
        if status == "Done":
            return QBrush(QColor("#bfecc2"))
        if status == "Failed":
            return QBrush(QColor("#ff9999"))
        return QBrush(QColor("#ffffff"))

# Graphics node for simple lane visualization
class GNode(QGraphicsRectItem):
    def __init__(self, nid: str, text: str, actor: str):
        super().__init__(-60, -20, 120, 40)
        self.nid = nid
        self.setPen(QPen(Qt.black))
        color = {"human": "#ffd37f", "robot": "#88ccff", "handover": "#d8a6ff"}.get(actor, "#cccccc")
        self.setBrush(QBrush(QColor(color)))
        txt = QGraphicsTextItem(text, self)
        txt.setDefaultTextColor(Qt.black)
        txt.setTextWidth(110)
        txt.setPos(-55, -10)

# Main window
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cooperative Planner (Human <-> Robot)")
        self.setGeometry(80, 80, 1100, 720)

        # graph model
        self.plan = GraphPlan()

        # UI elements
        self.human_table = TaskTable("Trạng thái Người")
        self.robot_table = TaskTable("Trạng thái Robot")

        # canvas for lanes
        self.view = QGraphicsView()
        self.scene = QGraphicsScene()
        self.view.setScene(self.scene)
        self.view.setMinimumHeight(220)

        # chat area + input
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.input = QLineEdit()
        self.input.returnPressed.connect(self.on_command)

        # top layout with tables and graph
        top_h = QHBoxLayout()
        left_v = QVBoxLayout()
        left_v.addWidget(self.human_table)
        left_v.addWidget(QLabel("Graph lanes (visualization)"))
        top_h.addLayout(left_v)
        top_h.addWidget(self.view)
        top_h.addWidget(self.robot_table)

        # bottom chat layout
        bottom_v = QVBoxLayout()
        bottom_v.addWidget(QLabel("Chat / Command (enter to send). Commands: task:, done?, ephemeral:, start, pause, resume, list, graph"))
        bottom_v.addWidget(self.chat)
        bottom_v.addWidget(self.input)

        # main layout
        main = QVBoxLayout()
        main.addLayout(top_h)
        main.addLayout(bottom_v)
        self.setLayout(main)

        # execution control
        self.exec_timer = QTimer()
        self.exec_timer.timeout.connect(self.exec_cycle)
        self.running = False

        # progress execution per node
        self.node_progress_timer = QTimer()
        self.node_progress_timer.timeout.connect(self.node_progress_update)
        self.current_executing: Dict[str, Dict] = {}  # nid -> {step, total_steps, table, row}

        # set up sample tasks (15 tasks split approx)
        self._init_sample_plan()
        self.redraw_all()

    # -----------------------------
    # Plan operations
    # -----------------------------
    def _init_sample_plan(self):
        samples = [
            ("robot", "pick cake"),
            ("robot", "place cake in Box2"),
            ("human", "pick teddy bear"),
            ("human", "place teddy bear in Box1"),
            ("robot", "pick toy car"),
            ("robot", "move toy car to human"),
            ("human", "pick toy car"),
            ("human", "place toy car in Box1"),
            ("human", "pick apple"),
            ("human", "move apple to robot"),
            ("robot", "pick apple"),
            ("robot", "place apple in Box2"),
            ("human", "pick banana"),
            ("robot", "pick orange"),
            ("human", "place banana in Box1"),
        ]
        # create nodes sequentially and link within lane
        last_in_lane = {"human": None, "robot": None, "handover": None}
        for actor, label in samples:
            node = ActionNode(label=label, actor=actor, duration=3.0)
            nid = self.plan.add_node(node)
            if last_in_lane[actor]:
                self.plan.add_edge(last_in_lane[actor], nid)
            last_in_lane[actor] = nid
        # Add some handovers edges to illustrate: robot move toy car to human -> link to human pick toy car
        # find corresponding nodes by label
        r_move = self.plan.find_by_label("move toy car")
        h_pick = self.plan.find_by_label("pick toy car")
        if r_move and h_pick:
            # insert a handover node between them
            ho = ActionNode("handover_toycar", "handover", duration=2.0)
            hoid = self.plan.add_node(ho)
            # connect r_move -> ho -> h_pick
            self.plan.remove_edge(next((a,b) for (a,b) in self.plan.edges if a == r_move and b == h_pick), ) if any( (a==r_move and b==h_pick) for (a,b) in self.plan.edges) else None
            self.plan.add_edge(r_move, hoid)
            self.plan.add_edge(hoid, h_pick)

    # -----------------------------
    # Graphical display (simple)
    # -----------------------------
    def redraw_all(self):
        # refresh tables
        self.human_table.clear()
        self.robot_table.clear()
        # populate tables from plan nodes in lane order (best-effort: follow edges within same actor)
        # We'll list nodes grouped by actor (not full topo).
        humans = [n for n in self.plan.nodes.values() if n.actor == "human"]
        robots = [n for n in self.plan.nodes.values() if n.actor == "robot"]

        # try to order by following chain starting from nodes without predecessors in same lane
        def order_lane(nodes_list, actor):
            # build adjacency for same actor
            idmap = {n.id: n for n in nodes_list}
            succ = {nid: [] for nid in idmap}
            preds = {nid: [] for nid in idmap}
            for (a,b) in self.plan.edges:
                if a in idmap and b in idmap:
                    succ[a].append(b)
                    preds[b].append(a)
            starts = [nid for nid in idmap if not preds[nid]]
            ordered = []
            for s in starts:
                cur = s
                while cur and cur not in ordered:
                    ordered.append(cur)
                    nexts = succ.get(cur,[])
                    cur = nexts[0] if nexts else None
            # append any remaining
            for nid in idmap:
                if nid not in ordered:
                    ordered.append(nid)
            return ordered

        human_order = order_lane(humans, "human")
        robot_order = order_lane(robots, "robot")

        for nid in human_order:
            node = self.plan.nodes[nid]
            self.human_table.add_row(node.label, node.status)
        for nid in robot_order:
            node = self.plan.nodes[nid]
            self.robot_table.add_row(node.label, node.status)

        # redraw simple lane view
        self.scene.clear()
        margin = 20
        lane_y = {"human": 40, "handover": 120, "robot": 200}
        spacing_x = 140
        pos_map = {}
        # place nodes per-lane left-to-right based on our order lists
        def place_nodes(order_list, actor):
            x = margin
            for nid in order_list:
                node = self.plan.nodes[nid]
                gn = GNode(nid, node.label, node.actor)
                gn.setPos(x, lane_y.get(actor, 120))
                self.scene.addItem(gn)
                pos_map[nid] = QPointF(x, lane_y.get(actor, 120))
                x += spacing_x
        place_nodes(human_order, "human")
        place_nodes([n.id for n in self.plan.nodes.values() if n.actor == "handover"], "handover")
        place_nodes(robot_order, "robot")
        # draw arrows for edges
        for (a,b) in self.plan.edges:
            if a in pos_map and b in pos_map:
                p1 = pos_map[a] + QPointF(0,0)
                p2 = pos_map[b] + QPointF(0,0)
                # line
                line = self.scene.addLine(p1.x()+60, p1.y()+20, p2.x()-60, p2.y()+20, QPen(Qt.black))

    # -----------------------------
    # Commands & chat
    # -----------------------------
    def chat_append(self, text: str):
        self.chat.append(text)

    def on_command(self):
        txt = self.input.text().strip()
        self.input.clear()
        if not txt:
            return
        self.chat_append(f"[User] {txt}")
        cmd = txt.strip()
        if cmd.lower().startswith("task:"):
            body = cmd[5:].strip()
            parts = body.split(" ", 1)
            if len(parts) < 2:
                self.chat_append("[System] ❌ Cú pháp: task: human|robot <description>")
                return
            who = parts[0].lower()
            lab = parts[1]
            if who not in ("human","robot"):
                self.chat_append("[System] ❌ Actor phải là human hoặc robot.")
                return
            node = ActionNode(lab, who)
            nid = self.plan.add_node(node)
            # append to end of lane: find any node in lane with no successor in lane -> link
            candidate = None
            for other_id, other in self.plan.nodes.items():
                if other.actor == who:
                    succs = [b for (a,b) in self.plan.edges if a == other_id and self.plan.nodes[b].actor == who]
                    if not succs:
                        candidate = other_id
                        break
            if candidate:
                self.plan.add_edge(candidate, nid)
            self.chat_append(f"[System] ✅ Added '{lab}' to {who}")
            self.redraw_all()

        elif cmd.lower().startswith("done?"):
            keyword = cmd[5:].strip()
            if not keyword:
                self.chat_append("[System] ❌ Usage: done? <keyword>")
                return
            nid = self.plan.find_by_label(keyword)
            if not nid:
                self.chat_append(f"[System] ❌ Không tìm thấy task chứa '{keyword}'")
                return
            node = self.plan.nodes[nid]
            if node.status == "Done":
                self.chat_append(f"[System] ✅ '{node.label}' already Done.")
                return
            # start executing that node (force) if allowed by preconditions: we simulate check
            preds = self.plan.predecessors(nid)
            if any(self.plan.nodes[p].status != "Done" for p in preds):
                self.chat_append("[System] ⚠ Một số predecessors chưa hoàn thành. Tuy nhiên bạn yêu cầu thực hiện: sẽ thực hiện sau khi ready (enforce).")
            # ensure it's dispatched by scheduler: mark ready flag by setting status to Pending (already)
            # we will start scheduler if not running, and it will pick it when predecessors done
            if not self.running:
                self.chat_append("[System] ▶ Starting scheduler (auto) to process tasks...")
                self.start_scheduler()
            # Also if predecessor done or no predecessor, we can prioritize by marking it 'high priority' -> simply nothing, scheduler will pick ready nodes
        elif cmd.lower().startswith("ephemeral:"):
            # ephemeral action - insert after currently executing node or after selecting keyword
            lab = cmd[len("ephemeral:"):].strip()
            if not lab:
                self.chat_append("[System] ❌ Usage: ephemeral: <label>")
                return
            # find currently executing node if any:
            cur = None
            for nid, info in self.current_executing.items():
                cur = nid
                break
            if not cur:
                self.chat_append("[System] ⚠ Không có node đang chạy - ephemeral sẽ chèn vào cuối lane of default human.")
                # fallback to append human
                node = ActionNode(lab, "human", ephemeral=True)
                nidnew = self.plan.add_node(node)
                # find chain tail
                tail = None
                for oid,o in self.plan.nodes.items():
                    if o.actor=="human":
                        succs = [b for (a,b) in self.plan.edges if a==oid and self.plan.nodes[b].actor=="human"]
                        if not succs:
                            tail = oid
                            break
                if tail:
                    self.plan.add_edge(tail, nidnew)
                self.chat_append(f"[System] ✅ Ephemeral '{lab}' appended to end of human lane.")
                self.redraw_all()
                return
            # otherwise insert after cur
            # if label exists somewhere else, remove old node
            old = self.plan.find_by_label(lab)
            if old:
                self.plan.remove_node(old)
                self.chat_append(f"[System] ⚠ Existing node with same label removed (migrated).")
            cur_node = self.plan.nodes[cur]
            # create ephemeral node with same actor as current
            ephemeral = ActionNode(lab, cur_node.actor, duration=2.0, ephemeral=True)
            newid = self.plan.add_node(ephemeral)
            # rewire successors: cur->succ => cur->new -> succ
            succs = self.plan.successors(cur)
            # remove edges cur->succ
            for s in succs:
                self.plan.remove_edge(cur, s)
            # add cur->new, new->succ for each
            self.plan.add_edge(cur, newid)
            for s in succs:
                self.plan.add_edge(newid, s)
            self.chat_append(f"[System] ✅ Ephemeral '{lab}' inserted after '{cur_node.label}'")
            self.redraw_all()

        elif cmd.lower() == "start":
            self.start_scheduler()
        elif cmd.lower() == "pause":
            self.stop_scheduler()
        elif cmd.lower() == "resume":
            self.start_scheduler()
        elif cmd.lower() == "list":
            # list tasks
            self.chat_append("[System] Tasks:")
            for nid, node in self.plan.nodes.items():
                self.chat_append(f" - ({node.actor}) {node.label} [{node.status}]")
        elif cmd.lower() == "graph":
            self.redraw_all()
            self.chat_append("[System] Graph redrawn.")
        else:
            self.chat_append("[System] ❌ Unknown command.")

    # -----------------------------
    # Scheduler
    # -----------------------------
    def start_scheduler(self):
        if not self.running:
            self.running = True
            self.exec_timer.start(500)  # scheduler loop every 0.5s
            self.chat_append("[System] Scheduler started.")
            # start node progress timer (for active nodes)
            if not self.node_progress_timer.isActive():
                self.node_progress_timer.start(300)
        else:
            self.chat_append("[System] Scheduler already running.")

    def stop_scheduler(self):
        if self.running:
            self.running = False
            self.exec_timer.stop()
            self.chat_append("[System] Scheduler paused.")
        else:
            self.chat_append("[System] Scheduler not running.")

    def exec_cycle(self):
        # pick ready nodes
        if not self.running:
            return
        ready = self.plan.topo_ready()
        # filter out nodes already in current_executing
        ready = [r for r in ready if r not in self.current_executing]
        # we allow parallel human and robot; also allow multiple nodes concurrently (simple)
        # but if node is handover, enforce that both sides coordinate: for prototype we just run it here
        for nid in ready:
            node = self.plan.nodes[nid]
            # dispatch node
            node.status = "In Progress"
            # find which table/row to update
            table, row = self.find_table_and_row_for_node(nid)
            if table is not None and row is not None:
                table.update_status_row(row, "In Progress")
            # add to current_executing with steps
            steps = max(1, int(node.duration / 0.3))  # number of progress steps
            self.current_executing[nid] = {"step": 0, "total": steps, "label": node.label, "table": table, "row": row, "actor": node.actor}
            self.chat_append(f"[System] ▶ Dispatch '{node.label}' ({node.actor})")
            # For handover we could set special behavior; prototype: treat same but mark
        # update UI if nothing ready
        self.redraw_all()

    def node_progress_update(self):
        if not self.current_executing:
            return

        to_finish = []
        progress_texts = []

        for nid, info in list(self.current_executing.items()):
            info["step"] += 1
            total = info["total"]
            percent = int((info["step"] / total) * 100)

            if info["step"] >= total:
                percent = 100
                to_finish.append(nid)

            progress_texts.append(f"{info['label']}: {percent}%")

        # Cập nhật tiến trình trên một dòng
        progress_line = "[System] " + " | ".join(progress_texts)
        cursor = self.chat.textCursor()
        cursor.movePosition(cursor.End)
        cursor.select(cursor.LineUnderCursor)
        cursor.removeSelectedText()
        cursor.insertText(progress_line)

        # Hoàn thành các node đã xong
        for nid in to_finish:
            self.finish_node(nid)

    def finish_node(self, nid: str):
        if nid not in self.plan.nodes:
            return
        node = self.plan.nodes[nid]
        node.status = "Done"
        # update table row
        table, row = self.find_table_and_row_for_node(nid)
        if table is not None and row is not None:
            table.update_status_row(row, "Done")
        self.chat_append(f"[System] ✅ Completed '{node.label}' ({node.actor})")
        # remove executing entry
        if nid in self.current_executing:
            del self.current_executing[nid]
        # if handover, ensure successors etc; prototype: just continue
        self.redraw_all()

    def find_table_and_row_for_node(self, nid: str):
        node = self.plan.nodes[nid]
        if node.actor == "human":
            # search label in human table
            r = self.human_table.find_row_by_text(node.label)
            return (self.human_table, r) if r is not None else (None, None)
        elif node.actor == "robot":
            r = self.robot_table.find_row_by_text(node.label)
            return (self.robot_table, r) if r is not None else (None, None)
        else:
            return (None, None)

# ------------------------------
# run app
# ------------------------------
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    win.chat_append("[System] Ready. Type 'start' to run scheduler, 'task:', 'done?', 'ephemeral:'.")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
