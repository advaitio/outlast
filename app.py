from __future__ import annotations

import streamlit as st

from repair_quest.ai import ai_available, analyze_item
from repair_quest.models import QuestAnalysis, RescueAction
from repair_quest.scoring import impact_summary
from repair_quest.seed import LEADERBOARD, PLAYERS
from repair_quest.state import complete_quest, create_quest, initialise_state, update_quest

st.set_page_config(
    page_title="Repair Quest",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem;}
    [data-testid="stSidebar"] {border-right: 1px solid #dce8d3;}
    .hero {
        padding: 1.4rem 1.6rem; border-radius: 20px;
        background: linear-gradient(120deg, #173f2c, #2d6a4f);
        color: white; margin-bottom: 1.5rem;
        box-shadow: 0 12px 30px rgba(24, 58, 44, .12);
    }
    .hero h1 {margin: 0 0 .25rem; color: white; font-size: 2.35rem;}
    .hero p {margin: 0; color: #eaf4e2; font-size: 1.05rem;}
    .eyebrow {text-transform: uppercase; letter-spacing: .12em; font-size: .72rem;
              font-weight: 800; color: #ffb38f;}
    .quest-card {
        background: white; border: 1px solid #dfe9d7; border-radius: 16px;
        padding: 1rem 1.1rem .8rem; margin-bottom: .45rem;
        min-height: 220px; box-shadow: 0 5px 16px rgba(24, 58, 44, .06);
    }
    .quest-card h3 {margin: .4rem 0 .25rem; font-size: 1.15rem; color: #183a2c;}
    .quest-card p {font-size: .92rem; color: #4f665c; margin: .3rem 0;}
    .pill {display:inline-block; padding:.2rem .55rem; margin-right:.25rem; border-radius:999px;
           background:#edf5e7; color:#28543e; font-size:.72rem; font-weight:700;}
    .pill.orange {background:#fff0e7; color:#b44319;}
    .status {font-size:.78rem; font-weight:800; color:#2d6a4f;}
    div[data-testid="stMetric"] {background:white; border:1px solid #dfe9d7; padding:.8rem 1rem;
                                border-radius:16px; box-shadow:0 5px 16px rgba(24,58,44,.05);}
    .small-note {color:#65766e; font-size:.82rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def hero(title: str, subtitle: str, eyebrow: str) -> None:
    content = (
        f'<div class="hero"><div class="eyebrow">{eyebrow}</div>'
        f"<h1>{title}</h1><p>{subtitle}</p></div>"
    )
    st.markdown(
        content,
        unsafe_allow_html=True,
    )


def flash_message() -> None:
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = None


def quest_card(quest: dict) -> None:
    action_icon = {"Repair": "🔧", "Rehome": "🏠", "Salvage": "♻️"}.get(quest["action"], "🛠️")
    helper_line = f" · Helping: {quest['helper']}" if quest.get("helper") else ""
    st.markdown(
        f"""
        <div class="quest-card">
          <span class="status">{quest["status"]}{helper_line}</span>
          <h3>{action_icon} {quest["title"]}</h3>
          <span class="pill orange">{quest["action"]}</span>
          <span class="pill">{quest["difficulty"]}</span>
          <span class="pill">~{quest["estimated_waste_kg"]} kg</span>
          <p>{quest["description"]}</p>
          <p><strong>First step:</strong> {quest["next_step"]}</p>
          <p class="small-note">Posted by {quest["owner"]}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    player = st.session_state.current_player
    col1, col2, col3 = st.columns(3)
    with col1:
        claim_disabled = quest["status"] != "Open" or quest["owner"] == player
        if st.button(
            "Claim",
            key=f"claim-{quest['id']}",
            use_container_width=True,
            disabled=claim_disabled,
        ):
            update_quest(quest["id"], status="Claimed", helper=player)
            st.session_state.flash = f"You claimed “{quest['title']}”."
            st.rerun()
    with col2:
        joined = player in quest.get("teammates", [])
        if st.button(
            "Joined ✓" if joined else "Join",
            key=f"join-{quest['id']}",
            use_container_width=True,
            disabled=joined or quest["owner"] == player or quest["status"] == "Completed",
        ):
            update_quest(quest["id"], teammates=[*quest.get("teammates", []), player])
            st.session_state.flash = f"You joined “{quest['title']}”."
            st.rerun()
    with col3:
        if st.button(
            "Offer part",
            key=f"offer-{quest['id']}",
            use_container_width=True,
            disabled=quest["status"] == "Completed",
        ):
            offer = f"{player} offered to check for a spare part"
            update_quest(quest["id"], offers=[*quest.get("offers", []), offer])
            st.session_state.flash = f"Your spare-part offer was added to “{quest['title']}”."
            st.rerun()

    with st.expander(
        f"Community help ({len(quest.get('suggestions', [])) + len(quest.get('offers', []))})"
    ):
        for message in [*quest.get("offers", []), *quest.get("suggestions", [])]:
            st.write(f"• {message}")
        with st.form(f"suggestion-{quest['id']}", clear_on_submit=True):
            suggestion = st.text_input(
                "Leave a quick suggestion",
                placeholder="Try checking the cable...",
            )
            submitted = st.form_submit_button("Post suggestion")
            if submitted and suggestion.strip():
                update_quest(
                    quest["id"],
                    suggestions=[*quest.get("suggestions", []), f"{player}: {suggestion.strip()}"],
                )
                st.session_state.flash = "Suggestion posted."
                st.rerun()


def discover_page() -> None:
    hero(
        "Rescue Board",
        "See what your community is saving—and jump into a quest.",
        "Discover",
    )
    flash_message()
    filter_col, count_col = st.columns([2, 1])
    with filter_col:
        selected_action = st.segmented_control(
            "Filter quests",
            ["All", "Repair", "Rehome", "Salvage"],
            default="All",
            label_visibility="collapsed",
        )
    quests = [quest for quest in st.session_state.quests if quest["status"] != "Completed"]
    if selected_action and selected_action != "All":
        quests = [quest for quest in quests if quest["action"] == selected_action]
    with count_col:
        st.caption(f"{len(quests)} active rescue opportunities")

    for index in range(0, len(quests), 2):
        columns = st.columns(2)
        for column, quest in zip(columns, quests[index : index + 2], strict=False):
            with column:
                quest_card(quest)


def analysis_panel(analysis: QuestAnalysis) -> None:
    icon = {RescueAction.REPAIR: "🔧", RescueAction.REHOME: "🏠", RescueAction.SALVAGE: "♻️"}[
        analysis.recommended_action
    ]
    st.subheader(f"{icon} {analysis.quest_title}")
    cols = st.columns(3)
    cols[0].metric("Recommendation", analysis.recommended_action.value)
    cols[1].metric("Difficulty", analysis.difficulty.value)
    cols[2].metric("Waste potentially saved", f"{analysis.estimated_waste_kg:g} kg")
    st.write(analysis.reason)
    st.info(f"**Safe first step:** {analysis.suggested_next_step}")


def rescue_page() -> None:
    hero(
        "Start a Rescue Quest",
        "Before replacing it, give your community one chance to save it.",
        "Rescue",
    )
    flash_message()
    create_tab, complete_tab = st.tabs(["Create a quest", "Complete a rescue"])

    with create_tab:
        st.caption(
            "AI mode is ready."
            if ai_available()
            else "Demo mode: add an OpenAI key to enable photo analysis."
        )
        left, right = st.columns([1, 1.2])
        with left:
            image = st.file_uploader("Photo of the item", type=["jpg", "jpeg", "png", "webp"])
            if image:
                st.image(image, caption="Item to rescue", use_container_width=True)
        with right:
            description = st.text_area(
                "What happened?",
                placeholder=(
                    "My desk fan stopped working yesterday. I was thinking of throwing it away."
                ),
                height=130,
            )
            if st.button("✨ Generate quest", type="primary", use_container_width=True):
                if not description.strip():
                    st.warning("Add a short description first.")
                else:
                    with st.spinner("Finding the best rescue path..."):
                        try:
                            st.session_state.analysis = analyze_item(
                                description.strip(),
                                image.getvalue() if image else None,
                                image.type if image else "image/jpeg",
                            ).model_dump(mode="json")
                            st.session_state.analysis_description = description.strip()
                        except Exception as exc:  # Streamlit should show a recoverable API error.
                            st.error(f"AI analysis failed: {exc}")

        if st.session_state.analysis:
            st.divider()
            analysis = QuestAnalysis.model_validate(st.session_state.analysis)
            analysis_panel(analysis)
            if st.button("Post to Rescue Board", type="primary"):
                quest = create_quest(analysis, st.session_state.analysis_description)
                st.session_state.analysis = None
                st.session_state.flash = f"“{quest['title']}” is now live on the Rescue Board."
                st.rerun()

    with complete_tab:
        active = [
            quest
            for quest in st.session_state.quests
            if quest["status"] != "Completed"
            and (
                quest["owner"] == st.session_state.current_player
                or quest.get("helper") == st.session_state.current_player
                or st.session_state.current_player in quest.get("teammates", [])
            )
        ]
        if not active:
            st.info("Claim or join a quest first, then come back to complete it.")
        else:
            labels = {quest["id"]: quest["title"] for quest in active}
            selected_id = st.selectbox(
                "Quest",
                labels,
                format_func=lambda quest_id: labels[quest_id],
            )
            outcome = st.radio(
                "What happened?",
                list(RescueAction),
                format_func=lambda value: {
                    RescueAction.REPAIR: "✅ Repaired",
                    RescueAction.REHOME: "🏠 Rehomed",
                    RescueAction.SALVAGE: "♻️ Parts reused",
                }[value],
                horizontal=True,
            )
            st.file_uploader(
                "After photo (optional for the prototype)",
                type=["jpg", "jpeg", "png", "webp"],
                key="after-photo",
            )
            if st.button("Complete rescue", type="primary"):
                points = complete_quest(selected_id, outcome)
                st.balloons()
                st.session_state.flash = (
                    f"Rescue complete! You earned {points} Impact Points."
                )
                st.rerun()


def impact_page() -> None:
    hero(
        "The community is on a roll",
        "Every repaired, rehomed, or salvaged item moves the community forward.",
        "Impact",
    )
    session_impact = impact_summary(st.session_state.quests)
    baseline = {"items_rescued": 12, "waste_avoided_kg": 7.4, "purchases_avoided": 4, "points": 620}
    total = {key: baseline[key] + session_impact[key] for key in baseline}

    cols = st.columns(4)
    cols[0].metric(
        "Items rescued",
        int(total["items_rescued"]),
        f"+{session_impact['items_rescued']} today",
    )
    cols[1].metric("Waste avoided", f"{total['waste_avoided_kg']:.1f} kg")
    cols[2].metric("Purchases avoided", int(total["purchases_avoided"]))
    cols[3].metric("Impact Points", int(total["points"]), f"+{session_impact['points']} today")

    progress = min(float(total["points"]) / 1_000, 1.0)
    st.subheader("Next community level: Circular Champions")
    st.progress(progress, text=f"{int(total['points'])} / 1,000 points")

    board_col, history_col = st.columns([1, 1.15])
    with board_col:
        st.subheader("Leaderboard")
        board = [row.copy() for row in LEADERBOARD]
        current_player = st.session_state.current_player
        current_row = next(row for row in board if row["player"] == current_player)
        current_row.update(
            items=current_row["items"] + int(session_impact["items_rescued"]),
            waste_kg=current_row["waste_kg"] + float(session_impact["waste_avoided_kg"]),
            points=current_row["points"] + int(session_impact["points"]),
        )
        board.sort(key=lambda row: row["points"], reverse=True)
        for rank, row in enumerate(board, start=1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
            st.markdown(
                f"**{medal} {row['player']}**  \n"
                f"{row['items']} rescues · {row['waste_kg']:.1f} kg · {row['points']} pts"
            )
    with history_col:
        st.subheader("Latest rescues")
        completed = [quest for quest in st.session_state.quests if quest["status"] == "Completed"]
        if not completed:
            st.info(
                "Complete a quest to add your first live result. "
                "Seeded community totals are shown for the demo."
            )
        for quest in completed:
            st.success(
                f"**{quest['item_name']}** — {quest['outcome']} · "
                f"{quest['estimated_waste_kg']} kg avoided · +{quest['points_awarded']} pts"
            )


initialise_state()

with st.sidebar:
    st.markdown("## 🛠️ Repair Quest")
    st.caption("Turn throwaways into community wins.")
    page = st.radio("Go to", ["Discover", "Rescue", "Impact"], label_visibility="collapsed")
    st.divider()
    st.session_state.current_player = st.selectbox(
        "Playing as",
        PLAYERS,
        index=PLAYERS.index(st.session_state.current_player),
    )
    st.caption("Hackathon demo profile · no sign-in needed")
    st.divider()
    if st.button("Reset demo data", use_container_width=True):
        for key in list(st.session_state):
            del st.session_state[key]
        st.rerun()

if page == "Discover":
    discover_page()
elif page == "Rescue":
    rescue_page()
else:
    impact_page()
