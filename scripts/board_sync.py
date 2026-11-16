#!/usr/bin/env python3
"""Borsagator board <-> issue sync — the custom layer over GitHub's built-in
project workflows (which cannot branch on labels, add comments/labels, close
with a reason, or read WSJF scores).

Runs from .github/workflows/board-sync.yml with a Borsagator App token.

Rules:
  - Card moved to Cancelled -> close issue as not_planned + 'cancelled' label + comment.
  - Card moved to Released  -> 'released' label + comment + close as completed
    (the built-in Auto-close workflow also closes; both paths are idempotent).
  - Issue closed as not_planned, or closed with the 'cancelled' label
    -> card to Cancelled (the built-in Item-closed workflow sends every
    close to Released, so this corrects the cancelled branch).
  - Closed issue labeled 'released'/'cancelled' afterwards -> card follows.
  - New issue whose body carries WSJF >= 6.0 -> card to Next. Fires on
    `opened` only: a later deliberate move by a human or the cycle is never
    overridden.
  - Issue assigned to moos-sherbo -> card to Doing (from Backlog/Next).
Digest issues are never touched.
"""
import json
import os
import re
import sys
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ["GH_TOKEN"]
ORG = "moos-labs"
REPO = "borsagator"
PROJECT_NUMBER = 1
WSJF_NEXT_THRESHOLD = 6.0
WORKER_LOGIN = "moos-sherbo"

RELEASED_COMMENT = (
    "Closed automatically \u2014 this issue's card was moved to "
    "**Released** on the Borsagator board."
)
CANCELLED_COMMENT = (
    "Closed automatically as **cancelled** \u2014 this issue's card was "
    "moved to **Cancelled** on the Borsagator board."
)


def req(method, path, body=None):
    r = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "borsagator-board-sync",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else {}


def gql(query, variables):
    out = req("POST", "/graphql", {"query": query, "variables": variables})
    if out.get("errors"):
        raise RuntimeError(f"GraphQL errors: {out['errors']}")
    return out["data"]


PROJECT_Q = """
query($org:String!,$num:Int!){ organization(login:$org){ projectV2(number:$num){
  id field(name:"Status"){ ... on ProjectV2SingleSelectField {
    id options { id name } } } } } }
"""

ISSUE_ITEM_Q = """
query($id:ID!){ node(id:$id){ ... on Issue {
  projectItems(first:20){ nodes { id project { id }
    fieldValueByName(name:"Status"){
      ... on ProjectV2ItemFieldSingleSelectValue { name } } } } } } }
"""

ITEM_Q = """
query($id:ID!){ node(id:$id){ ... on ProjectV2Item {
  project { id }
  fieldValueByName(name:"Status"){
    ... on ProjectV2ItemFieldSingleSelectValue { name } }
  content { ... on Issue { id number state title
    repository { nameWithOwner } } } } } }
"""

SET_STATUS = """
mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
  updateProjectV2ItemFieldValue(input:{ projectId:$p, itemId:$i,
    fieldId:$f, value:{ singleSelectOptionId:$o } }){ projectV2Item { id } } }
"""

ADD_ITEM = """
mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{ projectId:$p,
  contentId:$c }){ item { id } } }
"""


class Board:
    def __init__(self):
        data = gql(PROJECT_Q, {"org": ORG, "num": PROJECT_NUMBER})
        proj = data["organization"]["projectV2"]
        self.project_id = proj["id"]
        field = proj["field"]
        self.field_id = field["id"]
        self.options = {o["name"]: o["id"] for o in field["options"]}

    def issue_item(self, issue_node_id):
        """Return (item_id, status_name|None) for our project, or (None, None)."""
        data = gql(ISSUE_ITEM_Q, {"id": issue_node_id})
        for node in data["node"]["projectItems"]["nodes"]:
            if node["project"]["id"] == self.project_id:
                fv = node.get("fieldValueByName") or {}
                return node["id"], fv.get("name")
        return None, None

    def ensure_item(self, issue_node_id):
        item_id, status = self.issue_item(issue_node_id)
        if item_id:
            return item_id, status
        out = gql(ADD_ITEM, {"p": self.project_id, "c": issue_node_id})
        return out["addProjectV2ItemById"]["item"]["id"], None

    def set_status(self, item_id, name):
        gql(SET_STATUS, {"p": self.project_id, "i": item_id,
                         "f": self.field_id, "o": self.options[name]})


def is_digest(issue):
    title = issue.get("title") or ""
    labels = {l["name"] for l in issue.get("labels", [])}
    return "Borsagator digest" in title or "digest" in labels


def parse_wsjf(body):
    for line in (body or "").splitlines():
        if line.strip().startswith("WSJF:"):
            m = re.search(r"=\s*([0-9]+(?:\.[0-9]+)?)\s*$", line.strip())
            if m:
                return float(m.group(1))
    return None


def add_label(number, label):
    req("POST", f"/repos/{ORG}/{REPO}/issues/{number}/labels",
        {"labels": [label]})


def add_comment(number, text):
    comments = req("GET", f"/repos/{ORG}/{REPO}/issues/{number}/comments?per_page=100")
    if any(text in (c.get("body") or "") for c in comments):
        return
    req("POST", f"/repos/{ORG}/{REPO}/issues/{number}/comments", {"body": text})


def close_issue(number, reason):
    req("PATCH", f"/repos/{ORG}/{REPO}/issues/{number}",
        {"state": "closed", "state_reason": reason})


def main():
    with open(os.environ["GITHUB_EVENT_PATH"]) as fh:
        event = json.load(fh)
    event_name = os.environ["GITHUB_EVENT_NAME"]
    board = Board()

    if event_name == "issues":
        issue = event["issue"]
        if is_digest(issue):
            print("digest issue, skipping")
            return
        number = issue["number"]
        action = event["action"]

        if action == "opened":
            item_id, status = board.ensure_item(issue["node_id"])
            if status is None:
                board.set_status(item_id, "Backlog")
                status = "Backlog"
            score = parse_wsjf(issue.get("body"))
            if status == "Backlog" and score is not None and score >= WSJF_NEXT_THRESHOLD:
                board.set_status(item_id, "Next")
                print(f"#{number}: WSJF {score} >= {WSJF_NEXT_THRESHOLD} -> Next")

        elif action == "assigned":
            assignee = (event.get("assignee") or {}).get("login")
            if assignee == WORKER_LOGIN:
                item_id, status = board.issue_item(issue["node_id"])
                if item_id and status in ("Backlog", "Next"):
                    board.set_status(item_id, "Doing")
                    print(f"#{number}: assigned to {assignee} -> Doing")

        elif action == "closed":
            labels = {l["name"] for l in issue.get("labels", [])}
            item_id, status = board.issue_item(issue["node_id"])
            if not item_id:
                return
            if issue.get("state_reason") == "not_planned" or "cancelled" in labels:
                if status != "Cancelled":
                    board.set_status(item_id, "Cancelled")
                if "cancelled" not in labels:
                    add_label(number, "cancelled")
                print(f"#{number}: closed as cancelled -> card Cancelled")
            elif "released" in labels and status != "Released":
                board.set_status(item_id, "Released")
                print(f"#{number}: closed with 'released' label -> card Released")

        elif action == "labeled":
            label = (event.get("label") or {}).get("name")
            if issue.get("state") == "closed" and label in ("released", "cancelled"):
                item_id, status = board.issue_item(issue["node_id"])
                target = "Released" if label == "released" else "Cancelled"
                if item_id and status != target:
                    board.set_status(item_id, target)
                    print(f"#{number}: labeled {label} after close -> card {target}")

    elif event_name == "projects_v2_item":
        item = event["projects_v2_item"]
        data = gql(ITEM_Q, {"id": item["node_id"]})
        node = data["node"]
        if not node or node["project"]["id"] != board.project_id:
            return
        content = node.get("content") or {}
        if content.get("repository", {}).get("nameWithOwner") != f"{ORG}/{REPO}":
            return
        if "Borsagator digest" in (content.get("title") or ""):
            return
        status = (node.get("fieldValueByName") or {}).get("name")
        if content.get("state") != "OPEN":
            return
        number = content["number"]
        if status == "Cancelled":
            add_label(number, "cancelled")
            add_comment(number, CANCELLED_COMMENT)
            close_issue(number, "not_planned")
            print(f"#{number}: card -> Cancelled, issue closed as not_planned")
        elif status == "Released":
            add_label(number, "released")
            add_comment(number, RELEASED_COMMENT)
            close_issue(number, "completed")
            print(f"#{number}: card -> Released, issue closed as completed")

    else:
        print(f"unhandled event {event_name}")


if __name__ == "__main__":
    main()
