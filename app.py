"""Family Points Card - Streamlit app

Run:
    pip install streamlit
    streamlit run app.py

This app stores data locally in a JSON file next to the script.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime,timedelta
from pathlib import Path
from typing import Any
import os

import streamlit as st
AUTH_FILE = Path(__file__).with_name("accounts.json")
def load_accounts():

    if AUTH_FILE.exists():

        with AUTH_FILE.open("r", encoding="utf-8") as f:

            return json.load(f)

    return {

        "parent": "parent123",

        "son": "son123"

    }

def save_accounts(accounts):

    with AUTH_FILE.open("w", encoding="utf-8") as f:

        json.dump(accounts, f, indent=2)
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
            "auto_pay": {

                  "active": False,

                  "owe": 0,

                  "daily_pay": 20,

                 "last_paid_date": "",},
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
            st.error("Data file is invalid.")

            st.stop()

        return data
    except json.JSONDecodeError:
        st.error("Data file is corrupted.")
        st.stop()

    except FileNotFoundError:
        save_state(DEFAULT_STATE)

        return json.loads(json.dumps(DEFAULT_STATE))


def save_state(state: dict[str, Any]) -> None:

    tmp_file = DATA_FILE.with_suffix(".tmp")

    with tmp_file.open("w", encoding="utf-8") as f:

        json.dump(state, f, indent=2)

    os.replace(tmp_file, DATA_FILE)

def ensure_member(state: dict[str, Any], member_name: str) -> None:
    if member_name not in state["members"]:
        state["members"][member_name] = {
            "balance": 0,
            "rewards": [asdict(r) for r in DEFAULT_REWARDS],
            "history": [],
            "auto_pay": {

                   "active": False,

                   "owe": 0,

                  "daily_pay": 20,

                 "last_paid_date": "",},
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
def process_auto_pay(state, only_member: str | None = None):
    today = datetime.now().date()
    changed = False

    if only_member is None:
        members_iter = state["members"].items()
    else:
        if only_member not in state["members"]:
            return False
        members_iter = [(only_member, state["members"][only_member])]

    for member_name, member in members_iter:
        auto_pay = member.setdefault("auto_pay", {
            "active": False,
            "owe": 0,
            "daily_pay": 20,
            "last_paid_date": "",
        })

        if not auto_pay.get("active", False):
            continue

        owe = int(auto_pay.get("owe", 0))
        if owe <= 0:
            auto_pay["active"] = False
            continue

        daily_pay = int(auto_pay.get("daily_pay", 20))
        last_paid_str = auto_pay.get("last_paid_date", "")

        if last_paid_str:
            try:
                last_paid_date = datetime.strptime(last_paid_str, "%Y-%m-%d").date()
            except ValueError:
                last_paid_date = today - timedelta(days=1)
        else:
            last_paid_date = today - timedelta(days=1)

        days_due = (today - last_paid_date).days
        if days_due <= 0:
            continue

        payments_to_make = min(days_due, (owe + daily_pay - 1) // daily_pay)

        for _ in range(payments_to_make):
            owe = int(auto_pay.get("owe", 0))
            if owe <= 0:
                auto_pay["active"] = False
                break

            pay_amount = min(daily_pay, owe)

            if member["balance"] >= pay_amount:
                member["balance"] -= pay_amount
                auto_pay["owe"] = owe - pay_amount
                auto_pay["last_paid_date"] = today.strftime("%Y-%m-%d")
                add_history(
                    state,
                    member_name,
                    f"Auto paid {pay_amount} points",
                    -pay_amount
                )
                changed = True
            else:
                auto_pay["last_paid_date"] = today.strftime("%Y-%m-%d")
                add_history(
                    state,
                    member_name,
                    "Auto pay skipped (not enough points)",
                    0
                )
                changed = True
                break

        if auto_pay.get("owe", 0) <= 0:
            auto_pay["active"] = False

    return changed

def safe_member_index(member_names: list[str], selected: str) -> int:
    if selected in member_names:
        return member_names.index(selected)
    return 0


st.set_page_config(page_title=APP_TITLE, page_icon="💳", layout="wide")
st.title("💳 Family Points Card")
st.caption("A simple points wallet for chores, rewards, and parent-managed top-ups.")

state = load_state()
if process_auto_pay(state):

    save_state(state)
if not st.session_state.logged_in:

    st.title("🔐 Login")

    username = st.text_input("Username")

    password = st.text_input("Password", type="password")

    if st.button("Login"):

        accounts = load_accounts()
        if username in accounts and password == accounts[username]:
            st.session_state.role = "parent" if username == "parent" else "child"
            st.session_state.logged_in = True


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
member_names = list(state["members"].keys())

if not member_names:

    state["members"]["Son"] = {

        "balance": 0,

        "rewards": [asdict(r) for r in DEFAULT_REWARDS],

        "history": [],

        "auto_pay": {

            "active": False,

            "owe": 0,

            "daily_pay": 20,

            "last_paid_date": "",

        },

    }

    save_state(state)

    member_names = ["Son"]

if "selected_member" not in st.session_state:

    st.session_state.selected_member = member_names[0]

selected_member = st.session_state.selected_member

ensure_member(state, selected_member)

member = state["members"][selected_member]

# Sidebar: parent controls
with st.sidebar:
    st.divider()

    if st.button("Logout", use_container_width=True, key="logout_btn"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.unlocked = False
        st.rerun()

    if st.session_state.role == "parent":
        st.header("Parent controls")

        entered_pin = st.text_input(
            "PIN",
            type="password",
            placeholder="Enter PIN",
            key="entered_pin"
        )

        col_a, col_b = st.columns(2)

        with col_a:
            if st.button("Unlock", use_container_width=True, key="unlock_btn"):
                if entered_pin == state.get("pin", DEFAULT_PIN) or entered_pin == RECOVERY_PIN:
                    st.session_state.unlocked = True
                    st.session_state.message = "Parent mode unlocked."
                else:
                    st.session_state.message = "Wrong PIN."

        with col_b:
            if st.button("Lock", use_container_width=True, key="lock_btn"):
                st.session_state.unlocked = False
                st.session_state.message = "Parent mode locked."

        if st.session_state.unlocked:
            st.success("Unlocked")
        else:
            st.info("Locked")

        st.divider()
        st.subheader("Family members")

        new_member = st.text_input("Add a member", placeholder="Daughter", key="new_member")
        if st.button("Create member", use_container_width=True, key="create_member_btn"):
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
        if st.button("Delete member", use_container_width=True, key="delete_member_btn"):
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
        st.subheader("Password Settings")

        current_pw = st.text_input("Current Password", type="password", key="current_pw")
        new_pw = st.text_input("New Password", type="password", key="new_pw")

        if st.button("Save Password", key="save_password_btn"):
            accounts = load_accounts()
            username = "parent" if st.session_state.role == "parent" else "son"

            if accounts[username] != current_pw:
                st.session_state.message = "Current password is incorrect."
            elif len(new_pw.strip()) < 6:
                st.session_state.message = "Password must be at least 6 characters."
            else:
                accounts[username] = new_pw.strip()
                save_accounts(accounts)
                st.session_state.message = "Password updated."

        st.divider()
        st.subheader("Owe Points")

        owe_amount = st.number_input( "Points Owed",
                                      min_value=0,
                                      value=int(member.get("auto_pay", {}).get("owe", 0)),
                                      step=1,
                                      key="owe_amount"
                                      )

        daily_pay = st.selectbox(
            "Daily Payment",
            [10,20, 30,40,50,60],
            key="daily_payment")

        if st.button("💸 Run Autopay Now", use_container_width=True):
            if process_auto_pay(state, selected_member):
                save_state(state)
                st.session_state.message = "Autopay processed."
                st.rerun()

            else:
                st.session_state.message = "No autopay was needed."

        manual_pay_amount = st.number_input(
            "Manual Pay Amount",
            min_value=1,

            value=20,

            step=1,

            key="manual_pay_amount"
            )
        if st.button("💰 Manual Pay", use_container_width=True):

            member.setdefault("auto_pay", {})

            current_owe = int(member["auto_pay"].get("owe", 0))

            pay_amount = min(int(manual_pay_amount), current_owe)
            if pay_amount <= 0:
                st.session_state.message = "Nothing to pay."
            elif member["balance"] < pay_amount:
                st.session_state.message = "Not enough balance for manual pay."
            else:
                member["balance"] -= pay_amount
                member["auto_pay"]["owe"] = current_owe - pay_amount
                if member["auto_pay"]["owe"] <= 0:
                    member["auto_pay"]["active"] = False
                add_history(state,
                            selected_member,
                            f"Manual paid {pay_amount} points",
                            -pay_amount)

                save_state(state)

                st.session_state.message = f"Manually paid {pay_amount} points."

                st.rerun()

        if st.button("Save Owe Plan", key="save_owe_plan"):
            member.setdefault("auto_pay", {})

            member["auto_pay"]["active"] = owe_amount > 0

            member["auto_pay"]["owe"] = int(owe_amount)
    
            member["auto_pay"]["daily_pay"] = int(daily_pay)
   
            member["auto_pay"]["last_paid_date"] = ""

            save_state(state)

            st.session_state.message = "Owe plan saved."
        





        st.subheader("PIN settings")
        new_pin = st.text_input("Set new PIN", type="password", placeholder="New PIN", key="new_pin")
        if st.button("Save PIN", use_container_width=True, key="save_pin_btn"):
            if not st.session_state.unlocked:
                st.session_state.message = "Unlock first to change PIN."
            elif len(new_pin.strip()) < 4:
                st.session_state.message = "PIN should be at least 4 digits."
            else:
                state["pin"] = new_pin.strip()
                save_state(state)
                st.session_state.message = "PIN updated."

    else:
        st.header("Child Mode")
        st.info("Parent controls are not available.")
        st.session_state.unlocked = False

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
    auto_pay = member.get("auto_pay", {})

    st.subheader("Owe Status")

    st.write(f"Remaining Owe: {auto_pay.get('owe', 0)} points")

    if auto_pay.get("active"):

        st.write(

            f"Daily Payment: {auto_pay.get('daily_pay', 20)} points"

        )

    else:

        st.write("No active owe plan")

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
