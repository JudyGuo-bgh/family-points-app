"""Family Points Card - Streamlit app

Run:
    pip install streamlit
    streamlit run app.py

This app stores data locally in a JSON file next to the script.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st
if "logged_in" not in st.session_state:

    st.session_state.logged_in = False
    

APP_TITLE = "Family Points Card"
DATA_FILE = Path(__file__).with_name("family_points_data.json")
DEFAULT_PIN = "1234"
RECOVERY_PIN = "9999"   


@dataclass
class Reward:
    name: str
    cost: int


@dataclass
class Member:
    name: str
    balance: int = 0
    rewards: list[Reward] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)


DEFAULT_REWARDS = [
    Reward("Ice cream", 15),
    Reward("30min screen time", 30),
    Reward("Toy / small gift", 50),
    Reward("Movie Night",80)
]

DEFAULT_STATE = {
    "pin": DEFAULT_PIN,
    "members": {
        "son": {
            "balance": 100,
            "rewards": [asdict(r) for r in DEFAULT_REWARDS],
            "history": [],
        }
    },
}


def now_str() -> str:
    return datetime.now().strftime("%b %d, %Y %I:%M %p")


def load_state() -> dict[str, Any]:
    if not DATA_FILE.exists():
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))

    try:
        with DATA_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if "members" not in data:
            raise ValueError("Invalid state file")
        return data
    except Exception:
        save_state(DEFAULT_STATE)
        return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state: dict[str, Any]) -> None:
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def ensure_member(state: dict[str, Any], member_name: str) -> None:
    if member_name not in state["members"]:
        state["members"][member_name] = {
            "balance": 0,
            "rewards": [asdict(r) for r in DEFAULT_REWARDS],
            "history": [],
        }


def add_history(state: dict[str, Any], member_name: str, label: str, amount: int) -> None:
    state["members"][member_name]["history"].insert(
        0,
        {
            "time": now_str(),
            "label": label,
            "amount": amount,
        },
    )


def safe_member_index(member_names: list[str], selected: str) -> int:
    if selected in member_names:
        return member_names.index(selected)
    return 0


st.set_page_config(page_title=APP_TITLE, page_icon="💳", layout="wide")
st.title("💳 Family Points Card")
st.caption("A simple points wallet for chores, rewards, and parent-managed top-ups.")

state = load_state()
if not st.session_state.logged_in:

    st.title("🔐 Login")

    username = st.text_input("Username")

    password = st.text_input("Password", type="password")

    if st.button("Login"):

        if username == "parent" and password == "parent123":
            st.session_state.logged_in = True

            st.session_state.role = "parent"

            st.session_state.unlocked = False

            st.rerun()
        elif username == "son" and password == "son123":
            st.session_state.logged_in = True

            st.session_state.role = "child"

            st.session_state.unlocked = False

            st.rerun()

        else:

            st.error("Invalid username or password")

    st.stop()

# Session state
if "unlocked" not in st.session_state:
    st.session_state.unlocked = False
if st.session_state.get("role") == "child":

    st.session_state.unlocked = False
if "selected_member" not in st.session_state:
    st.session_state.selected_member = next(iter(state["members"].keys()))
if "message" not in st.session_state:
    st.session_state.message = ""
if "logged_in" not in st.session_state:

    st.session_state.logged_in = False

if "role" not in st.session_state:

    st.session_state.role = None

# Sidebar: parent controls
with st.sidebar:
    st.divider()

    if st.button("Logout", use_container_width=True):

        st.session_state.logged_in = False
  
        st.session_state.role = None
        st.session_state.unlocked = False

        st.rerun()
    if st.session_state.role == "parent":

        st.header("Parent controls")

        entered_pin = st.text_input(

            "PIN",

            type="password",

            placeholder="Enter PIN"

        )
    else:

        st.header("Child Mode")

        st.info("Parent controls are not available.")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Unlock", use_container_width=True):
            if entered_pin == state.get("pin", DEFAULT_PIN):
                st.session_state.unlocked = True
                st.session_state.message = "Parent mode unlocked."
            else:
                st.session_state.message = "Wrong PIN."
    with col_b:
        if st.button("Lock", use_container_width=True):
            st.session_state.unlocked = False
            st.session_state.message = "Parent mode locked."

    if st.session_state.unlocked:
        st.success("Unlocked")
    else:
        st.info("Locked")

    st.divider()
    st.subheader("Family members")

    new_member = st.text_input("Add a member", placeholder="Daughter")
    if st.button("Create member", use_container_width=True):
        if new_member.strip():
            ensure_member(state, new_member.strip())
            save_state(state)
            st.session_state.selected_member = new_member.strip()
            st.session_state.message = f"Created member: {new_member.strip()}"
            st.rerun()

    st.divider()
    st.subheader("Delete member")
    member_to_delete = st.selectbox(
        "Choose a member to delete",
        list(state["members"].keys()),
        key="delete_member_select",
    )
    if st.button("Delete member", use_container_width=True):
        if not st.session_state.unlocked:
            st.session_state.message = "Unlock parent mode first."
        elif len(state["members"]) <= 1:
            st.session_state.message = "At least one family member must remain."
        else:
            del state["members"][member_to_delete]
            save_state(state)
            remaining = list(state["members"].keys())
            st.session_state.selected_member = remaining[0]
            st.session_state.message = f"Deleted {member_to_delete}."
            st.rerun()

    st.divider()
    st.subheader("PIN settings")
    new_pin = st.text_input("Set new PIN", type="password", placeholder="New PIN")
    if st.button("Save PIN", use_container_width=True):
        if not st.session_state.unlocked:
            st.session_state.message = "Unlock first to change PIN."
        elif len(new_pin.strip()) < 4:
            st.session_state.message = "PIN should be at least 4 digits."
        else:
            state["pin"] = new_pin.strip()
            save_state(state)
            st.session_state.message = "PIN updated."

# Main layout
member_names = list(state["members"].keys())
if not member_names:
    state["members"]["Son"] = {
        "balance": 0,
        "rewards": [asdict(r) for r in DEFAULT_REWARDS],
        "history": [],
    }
    save_state(state)
    member_names = ["Son"]

selected_member = st.selectbox(
    "Select family member",
    member_names,
    index=safe_member_index(member_names, st.session_state.selected_member),
)
st.session_state.selected_member = selected_member
ensure_member(state, selected_member)
member = state["members"][selected_member]

if st.session_state.message:
    st.toast(st.session_state.message)
    st.session_state.message = ""

# Top cards
left, middle, right = st.columns([1.2, 1, 1])
with left:
    st.metric("Current balance", member["balance"])
with middle:
    st.metric("Rewards", len(member.get("rewards", [])))
with right:
    st.metric("History items", len(member.get("history", [])))

st.divider()

# Actions
add_col, redeem_col = st.columns(2)

with add_col:
    st.subheader("Add points")
    add_amount = st.number_input("Points to add", min_value=1, value=10, step=1)
    if st.button("Add points", use_container_width=True, disabled=not st.session_state.unlocked):
        member["balance"] += int(add_amount)
        add_history(state, selected_member, f"Added {int(add_amount)} points", int(add_amount))
        save_state(state)
        st.rerun()
    if not st.session_state.unlocked:
        st.caption("Unlock parent mode to add points.")

with redeem_col:
    st.subheader("Redeem points")
    redeem_amount = st.number_input(
        "Points to use",
        min_value=1,
        value=min(10, max(1, member["balance"])),
        step=1,
        max_value=max(1, member["balance"]),
    )
    can_redeem = (int(redeem_amount) <= member["balance"]and member["balance"] >= 100)
    if member["balance"] < 100:

        st.warning(

            f"You need at least 100 points before using points. "

            f"Current balance: {member['balance']}"

        )
    if st.button("Use points", use_container_width=True, disabled=not can_redeem):
        member["balance"] -= int(redeem_amount)
        add_history(state, selected_member, f"Redeemed {int(redeem_amount)} points", -int(redeem_amount))
        save_state(state)
        st.rerun()
    if member["balance"] == 0:
        st.caption("No points available.")

st.divider()

# Reward menu
reward_col, custom_col = st.columns([1.2, 1])

with reward_col:

    st.subheader("Reward menu")

    if member["balance"] < 100:

        st.warning(

            f"You need at least 100 points before redeeming rewards. "

            f"Current balance: {member['balance']}"

        )

    rewards = member.get("rewards", [])
    if not rewards:
        st.info("No rewards yet.")
    else:
        cols = st.columns(2)
        for i, reward in enumerate(rewards):
            with cols[i % 2]:
                affordable = (reward["cost"] <= member["balance"]and member["balance"] >= 100)
                st.markdown(f"**{reward['name']}**  \n{reward['cost']} points")
                if st.button(
                    f"Redeem {reward['name']}",
                    key=f"redeem_{i}_{reward['name']}",
                    use_container_width=True,
                    disabled=not affordable,
                ):
                    member["balance"] -= int(reward["cost"])
                    add_history(state, selected_member, f"Redeemed: {reward['name']}", -int(reward["cost"]))
                    save_state(state)
                    st.rerun()
                if member["balance"] < 100:
                    st.caption("Need at least 100 points before redeeming.")

                elif affordable:
                    st.caption("Available")

                else:
                    st.caption("Not enough points")

with custom_col:
    st.subheader("Add custom reward")
    reward_name = st.text_input("Reward name", placeholder="Pizza night")

    reward_cost = st.number_input("Cost", min_value=1, value=25, step=1)

    if st.button("Add reward", use_container_width=True, disabled=st.session_state.role != "parent"):
 
        if reward_name.strip():
            member.setdefault("rewards", []).append(

            {"name": reward_name.strip(), "cost": int(reward_cost)}

            )

            save_state(state)

            st.session_state.message = "Reward added."

            st.rerun()

    # Reset balance button

    if st.button(

        "Reset Balance to 0",

        use_container_width=True,

        disabled=not st.session_state.unlocked

    ):

        member["balance"] = 0

        save_state(state)

        st.session_state.message = "Balance reset to 0."

        st.rerun()

    if not st.session_state.unlocked:

        st.caption("Unlock parent mode to add custom rewards.")

st.divider()

# History
st.subheader("Recent activity")
history = member.get("history", [])
if history:
    for item in history[:10]:
        amt = item.get("amount", 0)
        delta = f"+{amt}" if amt > 0 else str(amt)
        st.write(f"**{item.get('label', '')}** — {delta} points  \n_{item.get('time', '')}_")
else:
    st.info("No activity yet.")

st.divider()

# Help
with st.expander("How it works"):
    st.write(
        "This app saves everything to a local JSON file. "
        "You can run it on your laptop and use it inside your family. "
        "For a more permanent setup, you can later move the data to SQLite."
    )
