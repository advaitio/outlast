from __future__ import annotations

from html import escape

import streamlit as st

from outlast import db
from outlast.ai import ai_available, analyze_item
from outlast.ai import disposal_guidance as generate_disposal_guidance
from outlast.models import (
    DisposalGuidance,
    PrePostGuidance,
    RescueAnalysis,
    RescueOutcome,
    RescueStatus,
)
from outlast.scoring import (
    COMPLETER_XP,
    CONTRIBUTOR_XP,
    SOLVER_XP,
    impact_summary,
    streak_length,
)
from outlast.seed import PLAYERS
from outlast.state import (
    add_suggestion,
    complete_rescue,
    create_rescue,
    initialise_state,
    refresh_from_database,
    repairs_helped_by,
    save_disposal_guidance,
)

st.set_page_config(page_title="Outlast", page_icon=":material/build:", layout="wide")

st.markdown(
    """
    <style>
    .leaderboard-card {
        display: flex;
        align-items: center;
        gap: 0.85rem;
        width: 100%;
        padding: 0.85rem 1rem;
        margin-bottom: 0.65rem;
        border: 1px solid #dbe8d5;
        border-radius: 12px;
        background: #ffffff;
        box-shadow: 0 3px 10px rgba(24, 58, 44, 0.06);
    }
    .leaderboard-card.leader {
        border-color: #f2c66d;
        background: linear-gradient(100deg, #fffaf0 0%, #ffffff 70%);
    }
    .leaderboard-rank {
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 2.35rem;
        height: 2.35rem;
        border-radius: 10px;
        background: #edf5e7;
        color: #28543e;
        font-size: 0.9rem;
        font-weight: 800;
    }
    .leaderboard-card.leader .leaderboard-rank {background: #fff0c7; color: #8b5b00;}
    .leaderboard-person {min-width: 0; flex: 1;}
    .leaderboard-name {font-size: 1rem; font-weight: 750; color: #183a2c;}
    .leaderboard-you {
        margin-left: 0.4rem;
        padding: 0.1rem 0.42rem;
        border-radius: 999px;
        background: #fff0e7;
        color: #b44319;
        font-size: 0.65rem;
        font-weight: 800;
        text-transform: uppercase;
    }
    .leaderboard-streak {margin-top: 0.12rem; color: #6a7d73; font-size: 0.78rem;}
    .leaderboard-score {text-align: right; color: #183a2c; font-size: 1.05rem; font-weight: 800;}
    .leaderboard-score span {
        display: block;
        color: #7b8a82;
        font-size: 0.66rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def show_flash() -> None:
    if message := st.session_state.flash:
        st.success(message)
        st.session_state.flash = None


def rescue_card(rescue: dict) -> None:
    with st.container(border=True):
        if rescue.get("image_bytes") or rescue.get("image_url"):
            st.image(
                rescue.get("image_bytes") or rescue["image_url"],
                caption=f"{rescue['item_name']} submitted as an item",
                width="stretch",
            )
        st.subheader(f":material/build: {rescue['title']}")
        st.caption(f"Posted by {rescue['owner']} · {rescue['status']}")
        st.write(rescue["description"])
        st.caption(
            f"{rescue['difficulty']} repair · about "
            f"{rescue['estimated_waste_kg']} kg of waste potentially avoided"
        )
        if rescue["owner"] == st.session_state.current_player:
            st.info(
                f"AI suggestion · Only visible to you: {rescue['next_step']}",
                icon=":material/auto_awesome:",
            )

        contributions = rescue["contributions"]
        with st.expander(f"Suggestions ({len(contributions)})"):
            if contributions:
                for contribution in contributions:
                    st.write(
                        f"👤 **Person suggestion · {contribution['player']}**: "
                        f"{contribution['message']}"
                    )
            else:
                st.caption("No suggestions yet. Share a useful next step.")
            with st.form(f"suggestion-{rescue['id']}", clear_on_submit=True):
                suggestion = st.text_input(
                    "Your suggestion", placeholder="Try checking the cable first…"
                )
                submitted = st.form_submit_button("Post suggestion", icon=":material/send:")
            if submitted:
                try:
                    xp, streak, _ = add_suggestion(rescue["id"], suggestion)
                    st.session_state.flash = (
                        f"Suggestion posted. You earned {xp} XP with a {streak}-day streak."
                    )
                    st.rerun()
                except (ValueError, db.PersistenceError) as exc:
                    st.warning(str(exc))


def show_rescue_photos(rescue: dict) -> None:
    before_image = rescue.get("image_bytes") or rescue.get("image_url")
    after_image = rescue.get("after_image_bytes") or rescue.get("after_image_url")
    if not before_image and not after_image:
        return
    image_columns = st.columns(2)
    if before_image:
        image_columns[0].image(before_image, caption="Before", width="stretch")
    if after_image:
        image_columns[1].image(after_image, caption="After", width="stretch")


def helped_rescue_card(rescue: dict, player: str) -> None:
    with st.container(border=True):
        st.subheader(f":material/handyman: {rescue['title']}")
        st.caption(f"Posted by {rescue['owner']} · {rescue['difficulty']} repair")
        solver_xp = rescue.get("solver_xp_awards", {}).get(player, 0)
        st.success(
            f"Repair completed · You earned {solver_xp} XP",
            icon=":material/check_circle:",
        )
        st.write(rescue["description"])
        player_contributions = [
            contribution
            for contribution in rescue.get("contributions", [])
            if contribution.get("player") == player
        ]
        st.markdown("**Your contribution**")
        if player_contributions:
            for contribution in player_contributions:
                st.write(contribution["message"])
        else:
            st.caption("You were recognised as a solver without a written suggestion.")
        show_rescue_photos(rescue)


def discover_page() -> None:
    st.title("Item board")
    st.caption("Help someone give a broken item one informed repair attempt.")
    show_flash()
    rescues = [rescue for rescue in st.session_state.rescues if rescue["status"] == "Open"]
    st.caption(f"{len(rescues)} open items")
    for index in range(0, len(rescues), 2):
        left, right = st.columns(2)
        for column, rescue in zip((left, right), rescues[index : index + 2], strict=False):
            with column:
                rescue_card(rescue)


def analysis_panel(analysis: RescueAnalysis) -> None:
    st.caption(":material/auto_awesome: Private AI assessment before you post")
    with st.container(border=True):
        st.subheader(analysis.rescue_title)
        assessment, facts = st.columns([2, 1], vertical_alignment="top")
        assessment_text = (
            f"**{analysis.pre_post_guidance.value}**\n\n"
            f"{analysis.reason}\n\n"
            f"**Recommended next action:** {analysis.suggested_next_step}"
        )
        with assessment:
            if analysis.pre_post_guidance == PrePostGuidance.POST_REPAIR:
                st.info(assessment_text, icon=":material/build:")
            else:
                st.warning(assessment_text, icon=":material/health_and_safety:")
                st.caption(
                    "This assessment is advisory. You can still post a repair request "
                    "if you disagree."
                )
        with facts:
            st.metric("Difficulty", analysis.difficulty.value)
            st.metric("Waste potentially saved", f"{analysis.estimated_waste_kg:g} kg")


def rescue_page() -> None:
    st.title("Add or resolve an item")
    show_flash()
    create_tab, complete_tab = st.tabs(["Add an item", "Resolve an item"])
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
                "Assess item", type="primary", icon=":material/auto_awesome:"
            )
        if generated:
            if not description.strip():
                st.warning("Add a short description first.")
            else:
                with st.spinner("Assessing whether a repair attempt makes sense…"):
                    try:
                        st.session_state.analysis = analyze_item(
                            description.strip(),
                            image.getvalue() if image else None,
                            image.type if image else "image/jpeg",
                        ).model_dump(mode="json")
                        st.session_state.analysis_description = description.strip()
                        st.session_state.analysis_image_bytes = (
                            image.getvalue() if image else None
                        )
                        st.session_state.analysis_image_mime = image.type if image else None
                    except Exception as exc:
                        st.error(f"AI analysis failed: {exc}")
        if st.session_state.analysis:
            analysis = RescueAnalysis.model_validate(st.session_state.analysis)
            analysis_panel(analysis)
            if st.session_state.analysis_image_bytes:
                st.caption("The uploaded photo will be attached to this item.")
            post_label = (
                "Post repair request"
                if analysis.pre_post_guidance == PrePostGuidance.POST_REPAIR
                else "Post repair request anyway"
            )
            if st.button(post_label, type="primary", icon=":material/publish:"):
                try:
                    rescue = create_rescue(
                        analysis,
                        st.session_state.analysis_description,
                        st.session_state.analysis_image_bytes,
                        st.session_state.analysis_image_mime,
                    )
                    st.session_state.analysis = None
                    st.session_state.analysis_description = ""
                    st.session_state.analysis_image_bytes = None
                    st.session_state.analysis_image_mime = None
                    st.session_state.flash = f"“{rescue['title']}” is now on the item board."
                    st.rerun()
                except db.PersistenceError as exc:
                    st.error(str(exc))

    with complete_tab:
        owned_open_rescues = [
            rescue
            for rescue in st.session_state.rescues
            if rescue["status"] == RescueStatus.OPEN.value
            and rescue["owner"] == st.session_state.current_player
        ]
        if not owned_open_rescues:
            st.info("Switch to the original poster to resolve one of their open items.")
        else:
            labels = {rescue["id"]: rescue["title"] for rescue in owned_open_rescues}
            with st.form("complete-rescue"):
                rescue_id = st.selectbox("Item", labels, format_func=labels.__getitem__)
                outcome = st.selectbox(
                    "Outcome", list(RescueOutcome), format_func=lambda value: value.value
                )
                solvers = st.multiselect(
                    "Who helped solve it?",
                    PLAYERS,
                    help=(
                        "Choose everyone the original poster wants to recognise for the repair. "
                        "Leave this blank for Recycle / dispose responsibly."
                    ),
                )
                after_image = st.file_uploader(
                    "After photo (optional)",
                    type=["jpg", "jpeg", "png", "webp"],
                    key="after-photo",
                )
                if after_image:
                    st.image(after_image, caption="Resolved item", width="stretch")
                completed = st.form_submit_button(
                    "Resolve item", type="primary", icon=":material/check_circle:"
                )
            if completed:
                try:
                    completion_award, solver_awards = complete_rescue(
                        rescue_id,
                        outcome,
                        solvers,
                        after_image.getvalue() if after_image else None,
                        after_image.type if after_image else None,
                    )
                    award_text = ", ".join(
                        f"{player} +{xp[0]} XP" for player, xp in solver_awards.items()
                    )
                    if outcome == RescueOutcome.RECYCLE_DISPOSE:
                        st.session_state.flash = "Item marked as recycled or responsibly disposed."
                    else:
                        st.session_state.flash = (
                            f"Item resolved. You earned {completion_award[0]} XP for resolving "
                            "it. "
                            f"Solver XP awarded: {award_text}."
                        )
                    st.balloons()
                    st.rerun()
                except (PermissionError, ValueError, db.PersistenceError) as exc:
                    st.warning(str(exc))


def impact_page() -> None:
    st.title("Community impact")
    st.caption(
        "Shared impact, with individual recognition for the people who contribute and solve."
    )
    session_impact = impact_summary(st.session_state.rescues)
    baseline = {
        "items_rescued": 12,
        "waste_avoided_kg": 7.4,
        "purchases_avoided": 4,
        "responsible_exits": 0,
    }
    total = {key: baseline[key] + session_impact[key] for key in baseline}
    left, middle, right, exits = st.columns(4)
    left.metric(
        "Items rescued", int(total["items_rescued"]), f"+{session_impact['items_rescued']} today"
    )
    middle.metric("Waste avoided", f"{total['waste_avoided_kg']:.1f} kg")
    right.metric("Purchases avoided", int(total["purchases_avoided"]))
    exits.metric("Responsible exits", int(total["responsible_exits"]))
    st.caption("Responsible exits are tracked separately and do not count as items rescued.")
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
            rank_label = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")
            current_player_badge = (
                '<span class="leaderboard-you">You</span>'
                if player == st.session_state.current_player
                else ""
            )
            leader_class = " leader" if rank == 1 else ""
            st.markdown(
                f"""
                <div class="leaderboard-card{leader_class}">
                    <div class="leaderboard-rank">{rank_label}</div>
                    <div class="leaderboard-person">
                        <div class="leaderboard-name">
                            {escape(player)}{current_player_badge}
                        </div>
                        <div class="leaderboard-streak">🔥 {streak}-day streak</div>
                    </div>
                    <div class="leaderboard-score">{stats['xp']}<span>XP</span></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.caption(
            f"Suggestion: {CONTRIBUTOR_XP} XP · Completing: {COMPLETER_XP} XP · "
            f"Solver: {SOLVER_XP} XP"
        )
    with history_col:
        st.subheader("Resolved items")
        completed = [
            rescue
            for rescue in st.session_state.rescues
            if rescue["status"] == RescueStatus.COMPLETED.value
        ]
        if not completed:
            st.info("Resolve an item to see it here.")
        for rescue in completed:
            solver_text = ", ".join(rescue["solvers"])
            if rescue["outcome"] == RescueOutcome.RECYCLE_DISPOSE.value:
                st.success(f"**{rescue['item_name']}** — recycled or responsibly disposed")
            else:
                st.success(
                    f"**{rescue['item_name']}** — {rescue['outcome']} · solved by {solver_text}"
                )
            show_rescue_photos(rescue)


def disposal_panel(rescue: dict) -> None:
    """Show owner-only, item-specific Singapore disposal guidance."""
    if rescue["status"] == RescueStatus.COMPLETED.value:
        return
    panel_key = f"disposal-panel-{rescue['id']}"

    def keep_panel_open() -> None:
        st.session_state[panel_key] = True

    with st.expander(
        "I have to let this item go",
        icon=":material/recycling:",
        key=panel_key,
        on_change="rerun",
    ):
        st.caption("Private to you · Guidance for when repair is not viable.")
        guidance_data = rescue.get("disposal_guidance")
        if not guidance_data:
            if st.button(
                "How to responsibly recycle or dispose this item?",
                key=f"disposal-guidance-{rescue['id']}",
                icon=":material/auto_awesome:",
                on_click=keep_panel_open,
            ):
                with st.spinner("Preparing disposal guidance…"):
                    try:
                        guidance = generate_disposal_guidance(
                            rescue["item_name"],
                            rescue["description"],
                            rescue.get("image_bytes"),
                            rescue.get("image_mime_type") or "image/jpeg",
                        )
                        save_disposal_guidance(rescue["id"], guidance)
                        guidance_data = guidance.model_dump(mode="json")
                    except (db.PersistenceError, PermissionError, ValueError) as exc:
                        st.warning(str(exc))
                    except Exception as exc:
                        st.error(f"Could not prepare disposal guidance: {exc}")
            if not guidance_data:
                return

        guidance = DisposalGuidance.model_validate(guidance_data)
        st.info(guidance.recommendation, icon=":material/location_on:")
        st.caption(guidance.category)
        st.markdown("**Before you recycle or dispose it**")
        for step in guidance.preparation_steps:
            st.write(f"• {step}")
        st.warning(guidance.safety_note, icon=":material/health_and_safety:")
        st.link_button(
            "Open official guidance",
            guidance.official_resource_url,
            icon=":material/open_in_new:",
        )
        st.caption(
            "To record this outcome, choose Recycle / dispose responsibly in Resolve an item."
        )


def my_rescues_page() -> None:
    st.title("My items")
    st.caption("Track repair requests you posted and repairs you helped solve.")
    show_flash()
    player = st.session_state.current_player
    posted_rescues = [
        rescue for rescue in st.session_state.rescues if rescue["owner"] == player
    ]
    helped_rescues = repairs_helped_by(st.session_state.rescues, player)
    posted_tab, helped_tab = st.tabs(
        [f"Posted by me ({len(posted_rescues)})", f"Helped by me ({len(helped_rescues)})"]
    )

    with posted_tab:
        if not posted_rescues:
            st.info("You have not posted an item yet. Add one from Items.")
        else:
            active_count = sum(
                rescue["status"] != RescueStatus.COMPLETED.value
                for rescue in posted_rescues
            )
            metrics = st.columns(3)
            metrics[0].metric("Posted", len(posted_rescues))
            metrics[1].metric("Active", active_count)
            metrics[2].metric("Completed", len(posted_rescues) - active_count)
            for index in range(0, len(posted_rescues), 2):
                columns = st.columns(2)
                for column, rescue in zip(
                    columns, posted_rescues[index : index + 2], strict=False
                ):
                    with column:
                        rescue_card(rescue)
                        disposal_panel(rescue)

    with helped_tab:
        if not helped_rescues:
            st.info(
                "No completed repairs yet. When an owner recognises you as a solver, "
                "the repair will appear here."
            )
        else:
            total_solver_xp = sum(
                rescue.get("solver_xp_awards", {}).get(player, 0)
                for rescue in helped_rescues
            )
            helped_metrics = st.columns(2)
            helped_metrics[0].metric("Repairs helped", len(helped_rescues))
            helped_metrics[1].metric("Solver XP earned", total_solver_xp)
            for index in range(0, len(helped_rescues), 2):
                columns = st.columns(2)
                for column, rescue in zip(
                    columns, helped_rescues[index : index + 2], strict=False
                ):
                    with column:
                        helped_rescue_card(rescue, player)


initialise_state()

with st.sidebar:
    st.title("Outlast")
    st.caption("Turn throwaways into community wins.")
    page = st.radio("Go to", ["Discover", "Items", "My Items", "Impact"])
    st.divider()
    st.session_state.current_player = st.selectbox(
        "Playing as", PLAYERS, index=PLAYERS.index(st.session_state.current_player)
    )
    stats = st.session_state.player_stats[st.session_state.current_player]
    current_streak = streak_length(stats["activity_dates"])
    st.caption(f"{stats['xp']} XP · {current_streak}-day streak")
    if db.available():
        if st.button("Refresh data", icon=":material/refresh:"):
            try:
                refresh_from_database()
                st.session_state.flash = "Latest community data loaded."
                st.rerun()
            except db.PersistenceError as exc:
                st.session_state.persistence_error = str(exc)
        if st.session_state.persistence_error:
            st.warning(st.session_state.persistence_error)
    if st.button("Reset demo data", icon=":material/restart_alt:"):
        for key in list(st.session_state):
            del st.session_state[key]
        st.rerun()

if page == "Discover":
    discover_page()
elif page == "Items":
    rescue_page()
elif page == "My Items":
    my_rescues_page()
else:
    impact_page()
