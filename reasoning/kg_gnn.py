"""
Simple Knowledge-Graph + lightweight GNN-based department classifier
Works for waste, pothole, municipality etc.
No external DB required. Only: pip install networkx torch numpy
"""

import networkx as nx
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

# Departments you want scored
DEPARTMENTS = [
    "Waste Management",
    "Construction",
    "Municipality",
    "Roads",
    "Electricity",
    "Water",
    "Ward Office"
]

class SimpleGNN(nn.Module):
    def __init__(self, in_dim, hidden_dim, out_dim):
        super().__init__()
        self.fc1 = nn.Linear(in_dim, hidden_dim)
        self.fc_msg = nn.Linear(hidden_dim, hidden_dim)
        self.fc_out = nn.Linear(hidden_dim, out_dim)

    def forward(self, features, adj, steps=2):
        h = F.relu(self.fc1(features))
        for _ in range(steps):
            m = torch.matmul(adj, h)
            h = F.relu(self.fc_msg(m))
        return torch.sigmoid(self.fc_out(h))


class KnowledgeGraphReasoner:
    def __init__(self):
        self.G = nx.DiGraph()

        # Add department nodes
        for d in DEPARTMENTS:
            self.G.add_node(d, type='dept')

        # Add attribute nodes
        self.attrs = [
            "large_waste", "hazardous_waste",
            "large_pothole", "deep_pothole",
            "near_electric", "near_water"
        ]

        for a in self.attrs:
            self.G.add_node(a, type='attr')

        # Connect attributes → departments
        edges = [
            ("large_waste", "Waste Management"),
            ("hazardous_waste", "Waste Management"),
            ("large_waste", "Ward Office"),
            ("deep_pothole", "Roads"),
            ("large_pothole", "Roads"),
            ("near_electric", "Electricity"),
            ("near_water", "Water")
        ]

        for u, v in edges:
            self.G.add_edge(u, v)

        # Node index
        self.nodes = list(self.G.nodes())
        self.node_index = {n: i for i, n in enumerate(self.nodes)}

        # Shape parameters
        self.in_dim = 8
        self.hidden_dim = 16
        self.out_dim = len(DEPARTMENTS)

        self.model = SimpleGNN(self.in_dim, self.hidden_dim, self.out_dim)

    # ---------------------------
    # FEATURE MATRIX
    # ---------------------------
    def build_feature_matrix(self, detection):
        N = len(self.nodes)
        feats = np.zeros((N, self.in_dim), dtype=np.float32)

        params = detection.get("params", {})
        t = detection.get("type")

        # Attribute triggers default
        attr_map = {a: False for a in self.attrs}

        # -------------------------
        # WASTE LOGIC
        # -------------------------
        if t == "waste":
            p = params.get("primary", {})
            if p:
                if p.get("area_pct", 0) > 0.02:
                    attr_map["large_waste"] = True

                cls = p.get("class_name", "").lower()
                if "battery" in cls or "chemical" in cls:
                    attr_map["hazardous_waste"] = True

        # -------------------------
        # POTHOLE LOGIC
        # -------------------------
        if t == "pothole":
            p = params.get("primary", {})
            if p:
                if p.get("area_pct", 0) > 0.01:
                    attr_map["large_pothole"] = True
                if p.get("est_depth_m", 0) > 0.05:
                    attr_map["deep_pothole"] = True

        # Apply attribute features
        for a in self.attrs:
            idx = self.node_index[a]
            val = 1.0 if attr_map[a] else 0.0
            feats[idx, 0] = val
            feats[idx, 1] = val

        # Dept node priors
        for d in DEPARTMENTS:
            idx = self.node_index[d]
            base = 2 + (idx % (self.in_dim - 2))
            feats[idx, base] = 0.1

        return torch.from_numpy(feats)

    # ---------------------------
    # ADJ MATRIX
    # ---------------------------
    def build_adj_matrix(self):
        N = len(self.nodes)
        adj = np.zeros((N, N), dtype=np.float32)

        for u, v in self.G.edges():
            ui, vi = self.node_index[u], self.node_index[v]
            adj[ui, vi] = 1
            adj[vi, ui] = 1

        # self loops
        for i in range(N):
            adj[i, i] = 1

        # row normalize
        adj = adj / adj.sum(axis=1, keepdims=True)
        return torch.from_numpy(adj)

    # ---------------------------
    # REASONING
    # ---------------------------
    def reason(self, record):
        feat = self.build_feature_matrix(record)
        adj = self.build_adj_matrix()

        with torch.no_grad():
            out = self.model(feat, adj)   # shape N x num_depts
            out = out.numpy()

        # Aggregate all node outputs
        total = out.sum(axis=0)

        # Normalize 0–1
        total = (total - total.min()) / (total.max() - total.min() + 1e-8)

        # Return dictionary
        return {dept: float(total[i]) for i, dept in enumerate(DEPARTMENTS)}


# -------------------------------------------------------------------
# EXAMPLE USAGE
# -------------------------------------------------------------------
if __name__ == "__main__":
    kg = KnowledgeGraphReasoner()

    example = {
        "type": "pothole",
        "params": {
            "primary": {
                "area_pct": 0.04,
                "est_depth_m": 0.12
            }
        }
    }

    scores = kg.reason(example)
    print(scores)
