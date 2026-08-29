from __future__ import annotations

import streamlit as st

from repair_quest.ai import ai_available, analyze_item
from repair_quest.models import RescueAction, RescueAnalysis, RescueStatus
from repair_quest.scoring import (
    CONTRIBUTOR_XP,
    SOLVER_XP,
    impact_summary,
    streak_length,
    streak_multiplier,
)
from repair_quest.seed import PLAYERS
from repair_quest.state import add_suggestion, complete_rescue, create_rescue, initialise_state

st.set_page_config(page_title="Repair Quest", page_icon=":material/build:", layout="wide")


def show_flash() -> None:
    if message := st.session_state.flash:
        st.success(message)
        st.session_state.flash = None


def rescue_card(rescue: dict) -> None:
    icons = {
        "Repair": ":material/build:",
        "Rehome": ":material/home:",
        "Salvage": ":material/recycling:",
    }
    with st.container(border=True):
        st.subheader(f"{icons[rescue['action']]} {rescue['title']}")
        st.caption(f"Posted by {rescue['owner']} · {rescue['status']}")
        st.write(rescue["description"])
        st.caption(
            f"{rescue['action']} · {rescue['difficulty']} · about "
            f"{rescue['estimated_waste_kg']} kg of waste potentially avoided"
        )
        st.info(f"Safe first step: {rescue['next_step']}", icon=":material/lightbulb:")

        contributions = rescue["contributions"]
        with st.expander(f"Suggestions ({len(contributions)})"):
            if contributions:
                for contribution in contributions:
                    st.write(f"**{contribution['player']}**: {contribution['message']}")
            else:
                st.caption("No suggestions yet. Share a useful next step.")
            with st.form(f"suggestion-{rescue['id']}", clear_on_submit=True):
                suggestion = st.text_input(
                    "Your suggestion", placeholder="Try checking the cable first…"
                )
                submitted = st.form_submit_button("Post suggestion", icon=":material/send:")
            if submitted:
                try:
                    xp, streak, multiplier = add_suggestion(rescue["id"], suggestion)
                    st.session_state.flash = (
                        f"Suggestion posted. You earned {xp} XP "
                        f"({CONTRIBUTOR_XP} × {multiplier:.2g}; {streak}-day streak)."
                    )
                    st.rerun()
                except ValueError as exc:
                    st.warning(str(exc))


def discover_page() -> None:
    st.title("Rescue board")
    st.caption("Find an item to help save with one useful suggestion.")
    show_flash()
    selected_action = st.segmented_control(
        "Filter rescues", ["All", "Repair", "Rehome", "Salvage"], default="All"
    )
    rescues = [rescue for rescue in st.session_state.rescues if rescue["status"] == "Open"]
    if selected_action and selected_action != "All":
        rescues = [rescue for rescue in rescues if rescue["action"] == selected_action]
    st.caption(f"{len(rescues)} open rescues")
    for index in range(0, len(rescues), 2):
        left, right = st.columns(2)
        for column, rescue in zip((left, right), rescues[index : index + 2], strict=False):
            with column:
                rescue_card(rescue)


def analysis_panel(analysis: RescueAnalysis) -> None:
    st.subheader(analysis.rescue_title)
    left, middle, right = st.columns(3)
    left.metric("Recommended path", analysis.recommended_action.value)
    middle.metric("Difficulty", analysis.difficulty.value)
    right.metric("Waste potentially saved", f"{analysis.estimated_waste_kg:g} kg")
    st.write(analysis.reason)
    st.info(f"Safe first step: {analysis.suggested_next_step}", icon=":material/lightbulb:")


def rescue_page() -> None:
    st.title("Start or complete a rescue")
    show_flash()
    create_tab, complete_tab = st.tabs(["Start a rescue", "Complete a rescue"])
    with create_tab:
        st.caption(
            "AI analysis is ready."
            if ai_available()
            else "Demo mode: add an OpenAI key for photo analysis."
        )
        with st.form("analyse-rescue"):
            image = st.file_uploader("Photo of the item", type=["jpg", "jpeg", "png", "webp"])
            description = st.text_area(
                "What happened?", placeholder="My desk fan stopped working yesterday."
            )
            generated = st.form_submit_button(
                "Generate rescue", type="primary", icon=":material/auto_awesome:"
            )
        if generated:
            if not description.strip():
                st.warning("Add a short description first.")
            else:
                with st.spinner("Finding the best rescue path…"):
                    try:
                        st.session_state.analysis = analyze_item(
                            description.strip(),
                            image.getvalue() if image else None,
                            image.type if image else "image/jpeg",
                        ).model_dump(mode="json")
                        st.session_state.analysis_description = description.strip()
                    except Exception as exc:
                        st.error(f"AI analysis failed: {exc}")
        if st.session_state.analysis:
            analysis = RescueAnalysis.model_validate(st.session_state.analysis)
            analysis_panel(analysis)
            if st.button("Post to rescue board", type="primary", icon=":material/publish:"):
                rescue = create_rescue(analysis, st.session_state.analysis_description)
                st.session_state.analysis = None
                st.session_state.flash = f"“{rescue['title']}” is now on the rescue board."
                st.rerun()

    with complete_tab:
        owned_open_rescues = [
            rescue
            for rescue in st.session_state.rescues
            if rescue["status"] == RescueStatus.OPEN.value
            and rescue["owner"] == st.session_state.current_player
        ]
        if not owned_open_rescues:
            st.info("Switch to the original poster to complete one of their open rescues.")
        else:
            labels = {rescue["id"]: rescue["title"] for rescue in owned_open_rescues}
            with st.form("complete-rescue"):
                rescue_id = st.selectbox("Rescue", labels, format_func=labels.__getitem__)
                outcome = st.selectbox(
                    "Outcome", list(RescueAction), format_func=lambda value: value.value
                )
                solvers = st.multiselect(
                    "Who solved it?",
                    PLAYERS,
                    help=(
                        "Choose everyone the original poster wants to recognise. "
                        "Each receives Solver XP."
                    ),
                )
                completed = st.form_submit_button(
                    "Complete rescue", type="primary", icon=":material/check_circle:"
                )
            if completed:
                try:
                    awards = complete_rescue(rescue_id, outcome, solvers)
                    award_text = ", ".join(f"{player} +{xp[0]} XP" for player, xp in awards.items())
                    st.session_state.flash = f"Rescue complete. Solver XP awarded: {award_text}."
                    st.balloons()
                    st.rerun()
                except (PermissionError, ValueError) as exc:
                    st.warning(str(exc))


def impact_page() -> None:
    st.title("Community impact")
    st.caption(
        "Shared impact, with individual recognition for the people who contribute and solve."
    )
    session_impact = impact_summary(st.session_state.rescues)
    baseline = {"items_rescued": 12, "waste_avoided_kg": 7.4, "purchases_avoided": 4}
    total = {key: baseline[key] + session_impact[key] for key in baseline}
    left, middle, right = st.columns(3)
    left.metric(
        "Items rescued", int(total["items_rescued"]), f"+{session_impact['items_rescued']} today"
    )
    middle.metric("Waste avoided", f"{total['waste_avoided_kg']:.1f} kg")
    right.metric("Purchases avoided", int(total["purchases_avoided"]))
    st.progress(
        min(total["items_rescued"] / 25, 1.0),
        text=f"{int(total['items_rescued'])} / 25 items toward the next community milestone",
    )

    board_col, history_col = st.columns(2)
    with board_col:
        st.subheader("XP leaderboard")
        board = sorted(
            st.session_state.player_stats.items(), key=lambda item: item[1]["xp"], reverse=True
        )
        for rank, (player, stats) in enumerate(board, start=1):
            streak = streak_length(stats["activity_dates"])
            multiplier = streak_multiplier(streak)
            st.write(
                f"**#{rank} {player}** — {stats['xp']} XP · {streak}-day streak · {multiplier:.2g}×"
            )
        st.caption(
            f"Suggestion: {CONTRIBUTOR_XP} XP × streak multiplier · "
            f"Solver: {SOLVER_XP} XP × streak multiplier"
        )
    with history_col:
        st.subheader("Completed rescues")
        completed = [
            rescue
            for rescue in st.session_state.rescues
            if rescue["status"] == RescueStatus.COMPLETED.value
        ]
        if not completed:
            st.info("Complete a rescue to see it here.")
        for rescue in completed:
            solver_text = ", ".join(rescue["solvers"])
            st.success(f"**{rescue['item_name']}** — {rescue['outcome']} · solved by {solver_text}")


initialise_state()

with st.sidebar:
    st.title("Repair Quest")
    st.caption("Turn throwaways into community wins.")
    page = st.radio("Go to", ["Discover", "Rescue", "Impact"])
    st.divider()
    st.session_state.current_player = st.selectbox(
        "Playing as", PLAYERS, index=PLAYERS.index(st.session_state.current_player)
    )
    stats = st.session_state.player_stats[st.session_state.current_player]
    current_streak = streak_length(stats["activity_dates"])
    st.caption(
        f"{stats['xp']} XP · {current_streak}-day streak · {streak_multiplier(current_streak):.2g}×"
    )
    if st.button("Reset demo data", icon=":material/restart_alt:"):
        for key in list(st.session_state):
            del st.session_state[key]
        st.rerun()

if page == "Discover":
    discover_page()
elif page == "Rescue":
    rescue_page()
else:
    impact_page()
