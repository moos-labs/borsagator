#!/usr/bin/env python3
"""Borsagator board <-> issue sync — the custom layer over GitHub's built-in
project workflows (which cannot branch on labels, add comments/labels, close
with a reason, or read WSJF scores).

Runs from .github/workflows/board-sync.yml with a Borsagator App token.

Note: the `projects_v2_item` Actions trigger is unusable for this org
project (adding it makes GitHub reject the whole workflow file — proven
2026-11-16 by bisection), so card moves are picked up two ways:
the built-in Auto-close workflow closes the issue when a card lands on
Released (this script then adds the label + comment from the resulting
`issues.closed` event), and a scheduled reconcile pass closes any still-open
issue whose card sits on Released or Cancelled.

VERIFICATION GATE (Muhammad, 2026-11-18 12:54 Cairo — board-fix issue #205):
the built-in Auto-close workflow STAYS ON, exactly as before. What changed
is that a card may sit on Released only after full verification for its
issue is complete. Verification is signalled by the 'verified' label, which
only the verified close-out procedure (scripts/verified_closeout.py:
evidence comment first, then the label, then close/move) may add. This
script enforces the gate on every path it controls:

  - An issue that arrives closed with its card on Released WITHOUT the
    'verified' label is an unverified auto-close: the gate reopens the
    issue, reverts the card to Doing, removes the 'released' label and
    posts the gate comment instead of the released label + comment.
  - The reconcile pass no longer closes an open issue whose card sits on
    Released unless it carries 'verified'; unverified Released cards are
    reverted to Doing with the gate comment.
  - Label-driven moves to Released (closed with / labelled 'released')
    only happen for 'verified' issues.
  - For promotion-type work, verification means: promotion merged +
    worker heartbeat on the new code (checkout_sha matches the merge) +
    live proof where the issue requires it (e.g. a sweep digest). The
    evidence comment posted by the close-out procedure records which of
    these were checked; this script checks only the resulting label.

Rules:
  - VERIFIED card on Released -> issue closed (built-in), then 'released'
    label + comment added here. UNVERIFIED -> gate above.
  - Card moved to Cancelled -> reconcile closes the issue as not_planned
    with the 'cancelled' label + comment.
  - Issue closed as not_planned, or closed with the 'cancelled' label
    -> card to Cancelled (the built-in Item-closed workflow sends every
    close to Released, so this corrects the cancelled branch).
  - Closed VERIFIED issue labeled 'released' afterwards -> card follows;
    'cancelled' labelling is unchanged.
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
GATE_COMMENT = (
    "**Verification gate:** this issue's card reached **Released** "
    "without the `verified` label, so the issue was reopened and the "
    "card was taken off Released. Cards go to Released only after all "
    "verification is complete (evidence comment + `verified` label, via "
    "the verified close-out procedure). Auto-close itself stays on \u2014 it "
    "now only ever closes verified work."
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

SET_STATUS = """
mutation($p:ID!,$i:ID!,$f:ID!,$o:String!){
  updateProjectV2ItemFieldValue(input:{ projectId:$p, itemId:$i,
    fieldId:$f, value:{ singleSelectOptionId:$o } }){ projectV2Item { id } } }
"""

ADD_ITEM = """
mutation($p:ID!,$c:ID!){ addProjectV2ItemById(input:{ projectId:$p,
  contentId:$c }){ item { id } } }
"""

OPEN_ITEMS_Q = """
query($p:ID!,$cursor:String){ node(id:$p){ ... on ProjectV2 {
  items(first:100, after:$cursor){ pageInfo { hasNextPage endCursor }
    nodes { id fieldValueByName(name:"Status"){
      ... on ProjectV2ItemFieldSingleSelectValue { name } }
      content { ... on Issue { id number state title labels(first:20){ nodes { name } } } } } } } } }
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


def reopen_issue(number):
    req("PATCH", f"/repos/{ORG}/{REPO}/issues/{number}", {"state": "open"})


def remove_label(number, label):
    try:
        req("DELETE", f"/repos/{ORG}/{REPO}/issues/{number}/labels/{label}")
    except Exception:  # noqa: BLE001 - label may already be absent
        pass


def issue_labels(content):
    return {n["name"] for n in ((content.get("labels") or {}).get("nodes") or [])}


def reconcile(board):
    """Close any OPEN issue whose card sits on Cancelled, or on Released
    WITH the 'verified' label. An unverified Released card is reverted to
    Doing by the verification gate instead of being closed."""
    cursor = None
    acted = 0
    while True:
        data = gql(OPEN_ITEMS_Q, {"p": board.project_id, "cursor": cursor})
        items = data["node"]["items"]
        for node in items["nodes"]:
            content = node.get("content") or {}
            if content.get("state") != "OPEN":
                continue
            if "Borsagator digest" in (content.get("title") or ""):
                continue
            status = (node.get("fieldValueByName") or {}).get("name")
            number = content["number"]
            if status == "Cancelled":
                add_label(number, "cancelled")
                add_comment(number, CANCELLED_COMMENT)
                close_issue(number, "not_planned")
                acted += 1
                print(f"reconcile: #{number} card Cancelled -> closed not_planned")
            elif status == "Released":
                if "verified" in issue_labels(content):
                    add_label(number, "released")
                    add_comment(number, RELEASED_COMMENT)
                    close_issue(number, "completed")
                    acted += 1
                    print(f"reconcile: #{number} verified card Released -> closed completed")
                else:
                    board.set_status(node["id"], "Doing")
                    add_comment(number, GATE_COMMENT)
                    acted += 1
                    print(f"reconcile: #{number} UNVERIFIED card Released -> gate reverted to Doing")
        if not items["pageInfo"]["hasNextPage"]:
            break
        cursor = items["pageInfo"]["endCursor"]
    print(f"reconcile done, {acted} issue(s) acted on")


def main():
    event_name = os.environ["GITHUB_EVENT_NAME"]
    board = Board()

    if event_name in ("schedule", "workflow_dispatch"):
        reconcile(board)
        return

    with open(os.environ["GITHUB_EVENT_PATH"]) as fh:
        event = json.load(fh)

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
            elif status == "Released":
                # Closed while the card sits on Released \u2014 in practice
                # the built-in Auto-close firing on a card move (it closes
                # as the user who moved the card, seconds after the move).
                # VERIFICATION GATE: only a 'verified' issue may stay here.
                if "verified" in labels:
                    if "released" not in labels:
                        add_label(number, "released")
                    add_comment(number, RELEASED_COMMENT)
                    print(f"#{number}: verified, closed with card on Released -> labeled + commented")
                else:
                    remove_label(number, "released")
                    board.set_status(item_id, "Doing")
                    reopen_issue(number)
                    add_comment(number, GATE_COMMENT)
                    print(f"#{number}: UNVERIFIED close on Released -> gate reopened + card reverted to Doing")
            elif "released" in labels and status != "Released":
                if "verified" in labels:
                    board.set_status(item_id, "Released")
                    print(f"#{number}: verified, closed with 'released' label -> card Released")
                else:
                    print(f"#{number}: 'released' label but NOT verified -> gate: card NOT moved to Released")
            elif status == "Cancelled":
                if "cancelled" not in labels:
                    add_label(number, "cancelled")
                add_comment(number, CANCELLED_COMMENT)
                print(f"#{number}: closed with card on Cancelled -> labeled + commented")

        elif action == "labeled":
            label = (event.get("label") or {}).get("name")
            if issue.get("state") == "closed" and label in ("released", "cancelled"):
                labels_now = {l["name"] for l in issue.get("labels", [])}
                if label == "released" and "verified" not in labels_now:
                    print(f"#{number}: labeled released after close but NOT verified -> gate: card NOT moved")
                else:
                    item_id, status = board.issue_item(issue["node_id"])
                    target = "Released" if label == "released" else "Cancelled"
                    if item_id and status != target:
                        board.set_status(item_id, target)
                        print(f"#{number}: labeled {label} after close -> card {target}")

    else:
        print(f"unhandled event {event_name}")


if __name__ == "__main__":
    main()
