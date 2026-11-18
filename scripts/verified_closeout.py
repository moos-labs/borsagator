#!/usr/bin/env python3
"""Verified close-out — the ONLY sanctioned way to land an issue on
Released (verification gate, board-fix issue #205, Muhammad 2026-11-18).

Usage: GH_TOKEN=... python3 scripts/verified_closeout.py <issue> <evidence-file>

The evidence file is posted as a comment BEFORE anything moves. It must
record the verification actually performed for the issue, e.g.:
  - code/tool issues: harness or test run on a fresh clone, with results;
  - promotion-type issues: promotion PR merged (SHA), worker heartbeat
    checkout_sha matching that merge, and live proof where required
    (e.g. the sweep digest issue number).

Steps (order matters):
  1. Refuse unless the issue is open and the evidence text is non-empty.
  2. Post the evidence comment.
  3. Add the 'verified' label — the gate signal board_sync enforces.
  4. Close the issue as completed.
  5. Move the card to Released and read back: issue closed, card
     Released, 'verified' present. The built-in Auto-close / Item-closed
     workflows stay on; with the label in place the gate lets this stand
     and board_sync adds the 'released' label + auto comment.

Raw GraphQL card moves to Released, label-only moves, and PR-merge-only
closes are NOT verified close-outs: board_sync reverts/reopens them.
"""
import json
import os
import sys
import urllib.request

API = "https://api.github.com"
TOKEN = os.environ["GH_TOKEN"]
ORG = "moos-labs"
REPO = "borsagator"
PROJECT_NUMBER = 1


def req(method, path, body=None):
    r = urllib.request.Request(
        API + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": "borsagator-verified-closeout",
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


def main():
    number = int(sys.argv[1])
    evidence = open(sys.argv[2], encoding="utf-8").read().strip()
    if len(evidence) < 40:
        raise SystemExit("evidence text too short — record what was verified")

    issue = req("GET", f"/repos/{ORG}/{REPO}/issues/{number}")
    if issue.get("state") != "open":
        raise SystemExit(f"#{number} is not open ({issue.get('state')})")
    if "Borsagator digest" in (issue.get("title") or ""):
        raise SystemExit("digest issues are never closed out this way")

    req("POST", f"/repos/{ORG}/{REPO}/issues/{number}/comments",
        {"body": evidence})
    print(f"#{number}: evidence comment posted")
    req("POST", f"/repos/{ORG}/{REPO}/issues/{number}/labels",
        {"labels": ["verified"]})
    print(f"#{number}: 'verified' label added")
    req("PATCH", f"/repos/{ORG}/{REPO}/issues/{number}",
        {"state": "closed", "state_reason": "completed"})
    print(f"#{number}: closed as completed")

    proj = gql(PROJECT_Q, {"org": ORG, "num": PROJECT_NUMBER})[
        "organization"]["projectV2"]
    options = {o["name"]: o["id"]
               for o in proj["field"]["options"]}
    items = gql(ISSUE_ITEM_Q, {"id": issue["node_id"]})["node"]["projectItems"]["nodes"]
    mine = [n for n in items if n["project"]["id"] == proj["id"]]
    if not mine:
        raise SystemExit(f"#{number} has no card on the board")
    item = mine[0]
    status = (item.get("fieldValueByName") or {}).get("name")
    if status != "Released":
        gql(SET_STATUS, {"p": proj["id"], "i": item["id"],
                         "f": proj["field"]["id"], "o": options["Released"]})
        print(f"#{number}: card -> Released")

    issue = req("GET", f"/repos/{ORG}/{REPO}/issues/{number}")
    items = gql(ISSUE_ITEM_Q, {"id": issue["node_id"]})["node"]["projectItems"]["nodes"]
    status = (items[0].get("fieldValueByName") or {}).get("name")
    labels = {l["name"] for l in issue.get("labels", [])}
    print(f"VERIFY #{number}: state={issue.get('state')} card={status} "
          f"labels={sorted(labels)}")
    assert issue.get("state") == "closed", "issue not closed on read-back"
    assert status == "Released", f"card not Released on read-back ({status})"
    assert "verified" in labels, "'verified' label missing on read-back"
    print(f"#{number}: verified close-out complete")


if __name__ == "__main__":
    main()
