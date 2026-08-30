from __future__ import annotations

from html import escape

import streamlit as st

from outlast import db
from outlast.ai import ai_available, analyze_item
from outlast.ai import disposal_guidance as generate_disposal_guidance
from outlast.ewaste import CATEGORY_LABELS, DATASET_URL, find_ewaste_points
from outlast.images import image_for_display
from outlast.models import DisposalGuidance, RescueAnalysis, RescueOutcome, RescueStatus
from outlast.scoring import (
    COMPLETER_XP,
    CONTRIBUTOR_XP,
    DISPOSAL_EVIDENCE_XP,
    SOLVER_XP,
    streak_length,
)
from outlast.seed import PLAYERS
from outlast.state import (
    add_suggestion,
    complete_rescue,
    create_rescue,
    delete_rescue,
    initialise_state,
    refresh_from_database,
    repairs_helped_by,
    save_disposal_guidance,
)

st.set_page_config(page_title="Outlast", page_icon=":material/build:", layout="wide")

PAGES = ("Dashboard", "Listings", "Report")
NEA_RECYCLING_GUIDANCE_URL = (
    "https://www.nea.gov.sg/our-services/waste-management/3r-programmes-and-resources/"
    "waste-minimisation-and-recycling"
)


def show_flash() -> None:
    if message := st.session_state.flash:
        st.success(message)
        st.session_state.flash = None
    if st.session_state.persistence_error:
        st.warning(st.session_state.persistence_error)


def top_bar() -> None:
    st.markdown(
        """
        <style>
        .outlast-brand { font-size: 2rem; font-weight: 700; letter-spacing: -0.02em; }
        .outlast-tagline { color: #6b7280; margin-top: -0.45rem; }
        .st-key-topbar [data-testid="stHorizontalBlock"] {
            display: grid;
            grid-template-columns: minmax(190px, 1fr) minmax(360px, 1.7fr) minmax(130px, 0.7fr);
            align-items: center;
            gap: 2rem;
        }
        .st-key-topbar [data-testid="stColumn"] {
            width: auto !important;
            min-width: 0;
            flex: none !important;
        }
        .st-key-topbar [data-testid="stColumn"]:last-child { justify-self: end; }
        .st-key-page [role="radiogroup"] {
            gap: 1.5rem;
            border: 0;
            background: transparent;
        }
        .st-key-page [role="radio"] {
            min-height: 2.5rem;
            padding-inline: 0.25rem;
            border: 0;
            border-bottom: 2px solid transparent;
            border-radius: 0;
            background: transparent !important;
            box-shadow: none !important;
        }
        .st-key-page [role="radio"][aria-checked="true"] {
            border-bottom-color: #b94a2a;
            background: transparent !important;
        }
        .listing-placeholder {
            aspect-ratio: 4 / 3; display: flex;
            align-items: center; justify-content: center; border-radius: 0.7rem;
            background: #edf3e7; color: #66736c; font-size: 0.8rem; font-weight: 500;
        }
        [class*="st-key-listing-"] { padding-block: 0.5rem; }
        [class*="st-key-listing-"] [data-testid="stImage"] img {
            width: 100%;
            aspect-ratio: 4 / 3;
            object-fit: cover;
            border-radius: 6px;
        }
        .impact-summary {
            margin-top: 0.65rem;
            margin-bottom: 1.25rem;
        }
        .impact-value {
            color: #183a2c;
            font-family: Manrope, Inter, sans-serif;
            font-size: clamp(2rem, 3.5vw, 3rem);
            font-weight: 650;
            letter-spacing: -0.025em;
            line-height: 1.1;
        }
        .impact-value strong { color: #b94a2a; font-weight: 700; }
        .metric-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            margin-top: 1rem;
            max-width: 52rem;
        }
        .metric-item {
            min-width: 0;
            padding: 0 1.25rem;
            border-left: 1px solid #d6e1d1;
        }
        .metric-item:first-child { padding-left: 0; border-left: 0; }
        .metric-label { color: #58675f; font-size: 0.78rem; font-weight: 500; }
        .metric-value {
            margin-top: 0.2rem;
            color: #183a2c;
            font-family: Manrope, Inter, sans-serif;
            font-size: 1.55rem;
            font-weight: 650;
            line-height: 1.15;
        }
        .leaderboard-card {
            display: flex; align-items: center; gap: 0.85rem; width: 100%;
            padding: 0.8rem 0; margin-bottom: 0;
            border: 0; border-bottom: 1px solid #dbe8d5; background: transparent;
        }
        .leaderboard-card.leader {
            border-bottom-color: #dbe8d5;
            background: transparent;
        }
        .leaderboard-card.current {
            padding-left: 0.75rem;
            border-left: 3px solid #b94a2a;
        }
        .leaderboard-rank {
            flex: 0 0 1.5rem;
            color: #66736c; font-size: 0.85rem; font-weight: 600;
        }
        .leaderboard-card.leader .leaderboard-rank {color: #28543e;}
        .leaderboard-person {min-width: 0; flex: 1;}
        .leaderboard-name {font-size: 1rem; font-weight: 750; color: #183a2c;}
        .leaderboard-you {
            margin-left: 0.4rem; color: #963d25; font-size: 0.65rem;
            font-weight: 600; text-transform: uppercase;
        }
        .leaderboard-streak {margin-top: 0.12rem; color: #6a7d73; font-size: 0.78rem;}
        .leaderboard-score {
            text-align: right; color: #183a2c; font-size: 1.05rem; font-weight: 800;
        }
        .leaderboard-score span {
            display: block; color: #7b8a82; font-size: 0.66rem; font-weight: 700;
            letter-spacing: 0.08em; text-transform: uppercase;
        }
        .st-key-report-panel {
            padding: 1.1rem 1.25rem 0.4rem;
            border: 0;
            border-radius: 6px;
            background: #edf3e7;
        }
        .st-key-report-panel [data-testid="stVerticalBlock"] { gap: 0.75rem; }
        .st-key-assessment-panel {
            padding-top: 1.25rem;
            border-top: 1px solid #d6e1d1;
        }
        .st-key-listing-dialog-image [data-testid="stImage"] {
            display: flex;
            align-items: center;
            justify-content: center;
            max-height: 55vh;
            min-height: 12rem;
            overflow: hidden;
            border-radius: 6px;
            background: #f4f1e8;
        }
        .st-key-listing-dialog-image [data-testid="stImage"] img {
            width: auto !important;
            max-width: 100%;
            max-height: 55vh;
            object-fit: contain;
            border-radius: 0;
        }
        @media (max-width: 640px) {
            .st-key-topbar [data-testid="stHorizontalBlock"] {
                grid-template-columns: minmax(0, 1fr) auto;
                gap: 0.75rem 1rem;
            }
            .st-key-topbar [data-testid="stColumn"]:nth-child(1) {
                grid-column: 1;
                grid-row: 1;
            }
            .st-key-topbar [data-testid="stColumn"]:nth-child(2) {
                grid-column: 1 / -1;
                grid-row: 2;
            }
            .st-key-topbar [data-testid="stColumn"]:nth-child(3) {
                grid-column: 2;
                grid-row: 1;
            }
            .st-key-page [role="radiogroup"] {
                justify-content: space-between;
                gap: 0.5rem;
            }
            .metric-grid {
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 1rem 0;
            }
            .metric-item { padding-inline: 0; border-left: 0; }
            .metric-item:nth-child(even) {
                padding-left: 1rem;
                border-left: 1px solid #d6e1d1;
            }
            .metric-value { font-size: 1.4rem; }
            h1 { font-size: 32px !important; line-height: 1.18 !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container(key="topbar"):
        brand, navigation, profile = st.columns(
            [3.2, 4.2, 2.4], vertical_alignment="center"
        )
        with brand:
            st.markdown('<div class="outlast-brand">Outlast</div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="outlast-tagline">Repair first. A pilot for NUS students.</div>',
                unsafe_allow_html=True,
            )
        with navigation:
            st.segmented_control(
                "Navigation",
                PAGES,
                key="page",
                label_visibility="collapsed",
                width="stretch",
            )
        with profile:
            stats = st.session_state.player_stats[st.session_state.current_player]
            with st.popover(
                st.session_state.current_player,
                icon=":material/account_circle:",
                type="tertiary",
                width="content",
            ):
                st.selectbox("Playing as", PLAYERS, key="current_player")
                st.caption(
                    f"{stats['xp']} XP · "
                    f"{streak_length(stats['activity_dates'])}-day streak"
                )
                refresh_clicked = st.button(
                    "Refresh community data",
                    icon=":material/refresh:",
                    key="refresh-community-data",
                    help="Load the latest shared listings and scores",
                    disabled=not db.available(),
                    width="stretch",
                )
        if refresh_clicked:
            try:
                refresh_from_database()
                st.session_state.flash = "Latest community data loaded."
                st.rerun()
            except db.PersistenceError as exc:
                st.session_state.persistence_error = str(exc)


def image_source(rescue: dict, after: bool = False) -> bytes | str | None:
    prefix = "after_" if after else ""
    return rescue.get(f"{prefix}image_bytes") or rescue.get(f"{prefix}image_url")


def show_listing_image(rescue: dict, full: bool = False) -> None:
    image = image_source(rescue)
    if image:
        display_image = image_for_display(image)
        if full:
            with st.container(key="listing-dialog-image"):
                st.image(display_image)
        else:
            st.image(display_image, width="stretch")
    else:
        st.markdown('<div class="listing-placeholder">No photo</div>', unsafe_allow_html=True)


def listing_card(rescue: dict, context: str) -> None:
    with st.container(key=f"listing-{context}-{rescue['id']}"):
        widths = [1.35, 1.65] if context.startswith("dashboard-") else [1.15, 1.85]
        image_col, details_col = st.columns(widths, vertical_alignment="center")
        with image_col:
            show_listing_image(rescue)
        with details_col:
            st.subheader(rescue["title"])
            st.caption(
                f"{rescue['difficulty']} repair · "
                f"{rescue['estimated_waste_kg']:g} kg potential waste avoided"
            )
            status = (
                ":green[:material/check_circle: Completed]"
                if rescue["status"] == RescueStatus.COMPLETED.value
                else ":orange[:material/pending: Open]"
            )
            st.markdown(f"{status} · Posted by {rescue['owner']}")
            if st.button(
                "View item", key=f"view-{context}-{rescue['id']}", width="stretch"
            ):
                listing_dialog(rescue)


def contribution_form(rescue: dict) -> None:
    st.markdown("#### Contribute to this repair")
    with st.form(f"contribution-{rescue['id']}", clear_on_submit=True):
        message = st.text_area(
            "Your suggestion", placeholder="Try checking the cable and fuse first.", max_chars=280
        )
        submitted = st.form_submit_button("Post contribution", type="primary")
    if submitted:
        try:
            xp, streak, _ = add_suggestion(rescue["id"], message)
            st.session_state.flash = (
                f"Contribution posted. You earned {xp} XP with a {streak}-day streak."
            )
            st.rerun()
        except (ValueError, db.PersistenceError) as exc:
            st.warning(str(exc))


def disposal_guidance_panel(rescue: dict) -> None:
    if rescue["status"] == RescueStatus.COMPLETED.value:
        return
    with st.expander("Need responsible disposal guidance?"):
        guidance_data = rescue.get("disposal_guidance")
        if not guidance_data and st.button(
            "Generate private disposal guidance",
            key=f"disposal-{rescue['id']}",
            icon=":material/auto_awesome:",
        ):
            try:
                with st.spinner("Preparing guidance…"):
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
        if guidance_data:
            guidance = DisposalGuidance.model_validate(guidance_data)
            st.info(guidance.recommendation)
            for step in guidance.preparation_steps:
                st.write(f"• {step}")
            st.caption(guidance.safety_note)
            st.link_button("Open official guidance", NEA_RECYCLING_GUIDANCE_URL)
            st.markdown("#### Official e-waste collection points")
            st.caption(
                "Filter the official NEA dataset by what the collection point accepts. "
                "These results are not ranked by distance."
            )
            category = st.selectbox(
                "What does the collection point need to accept?",
                CATEGORY_LABELS,
                key=f"ewaste-category-{rescue['id']}",
            )
            search = st.text_input(
                "Search by neighbourhood, building, street, or postal code",
                key=f"ewaste-search-{rescue['id']}",
                placeholder="For example: Jurong or 648886",
            )
            points = find_ewaste_points(category, search)
            if not points:
                st.info("No matching collection points found. Try a broader search or filter.")
            for point in points:
                with st.container(border=True):
                    st.write(f"**{point.display_name}**")
                    st.caption(point.address)
                    st.caption(f"Accepts: {point.accepted_items}")
                    maps, official = st.columns(2)
                    maps.link_button(
                        "View on OpenStreetMap",
                        point.openstreetmap_url,
                        icon=":material/location_on:",
                        width="stretch",
                    )
                    if point.official_url:
                        official.link_button(
                            "Programme details",
                            point.official_url,
                            icon=":material/open_in_new:",
                            width="stretch",
                        )
            st.caption("Location data: NEA via data.gov.sg. Verify before visiting.")
            st.link_button("View the official dataset", DATASET_URL)


def owner_actions(rescue: dict) -> None:
    if rescue["status"] == RescueStatus.COMPLETED.value:
        st.success(f"Resolved as: {rescue['outcome']}")
        if rescue.get("disposal_location"):
            st.write(f"Collection point used: {rescue['disposal_location']}")
        if rescue.get("solvers"):
            st.write(f"Recognised solvers: {', '.join(rescue['solvers'])}")
        after_image = image_source(rescue, after=True)
        if after_image:
            caption = (
                "Collection-point evidence"
                if rescue["outcome"] == RescueOutcome.RECYCLE_DISPOSE.value
                else "After"
            )
            st.image(after_image, caption=caption, width="stretch")
        return

    st.markdown("#### Manage your listing")
    disposal_guidance_panel(rescue)
    outcome = st.selectbox(
        "Outcome",
        list(RescueOutcome),
        format_func=lambda value: value.value,
        key=f"outcome-{rescue['id']}",
    )
    disposal_location: str | None = None
    if outcome == RescueOutcome.RECYCLE_DISPOSE:
        st.caption("Choose the exact NEA collection point used to close this item responsibly.")
        search = st.text_input(
            "Search collection point",
            key=f"resolve-ewaste-search-{rescue['id']}",
            placeholder="Neighbourhood, building, street, or postal code",
        )
        points = find_ewaste_points("All e-waste points", search, limit=25)
        if points:
            selected_point = st.selectbox(
                "Exact NEA collection point",
                points,
                format_func=lambda point: f"{point.display_name} — {point.address}",
                key=f"resolve-ewaste-location-{rescue['id']}",
            )
            disposal_location = f"{selected_point.display_name} — {selected_point.address}"
        else:
            st.warning("No collection point matches that search. Try a broader search.")
        st.caption(
            f"Optional evidence photo earns +{DISPOSAL_EVIDENCE_XP} XP before "
            "your streak multiplier."
        )
        solvers: list[str] = []
        after_image = st.file_uploader(
            "Collection-point evidence (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"after-{rescue['id']}",
        )
    else:
        solvers = st.multiselect(
            "Who helped solve it?",
            [player for player in PLAYERS if player != rescue["owner"]],
            help="Select the community members who solved this item.",
        )
        after_image = st.file_uploader(
            "After photo (optional)",
            type=["jpg", "jpeg", "png", "webp"],
            key=f"after-{rescue['id']}",
        )
    submitted = st.button("Resolve item", type="primary", key=f"resolve-{rescue['id']}")
    if submitted:
        try:
            completion_award, solver_awards = complete_rescue(
                rescue["id"],
                outcome,
                solvers,
                after_image.getvalue() if after_image else None,
                after_image.type if after_image else None,
                disposal_location,
            )
            solver_text = ", ".join(
                f"{player} +{award[0]} XP" for player, award in solver_awards.items()
            )
            if outcome == RescueOutcome.RECYCLE_DISPOSE:
                evidence_bonus = (
                    round(DISPOSAL_EVIDENCE_XP * completion_award[2]) if after_image else 0
                )
                st.session_state.flash = (
                    f"Item marked as responsibly disposed at {disposal_location}. "
                    f"You earned {completion_award[0]} XP."
                    + (f" Evidence bonus: +{evidence_bonus} XP." if evidence_bonus else "")
                )
            else:
                st.session_state.flash = (
                    f"Item resolved. You earned {completion_award[0]} XP. "
                    f"Solver awards: {solver_text}."
                )
            st.rerun()
        except (PermissionError, ValueError, db.PersistenceError) as exc:
            st.warning(str(exc))

    if st.button("Delete open listing", key=f"delete-{rescue['id']}"):
        st.session_state[f"confirm-delete-{rescue['id']}"] = True
    if st.session_state.get(f"confirm-delete-{rescue['id']}"):
        st.warning("Delete this open listing? Its contributions will be removed as well.")
        confirm, cancel = st.columns(2)
        if confirm.button("Yes, delete", key=f"confirm-delete-{rescue['id']}", type="primary"):
            try:
                delete_rescue(rescue["id"])
                st.session_state.flash = "Listing deleted."
                st.rerun()
            except (PermissionError, ValueError, db.PersistenceError) as exc:
                st.warning(str(exc))
        if cancel.button("Cancel", key=f"cancel-delete-{rescue['id']}"):
            st.session_state.pop(f"confirm-delete-{rescue['id']}", None)
            st.rerun()


@st.dialog("Item listing", width="large")
def listing_dialog(rescue: dict) -> None:
    st.title(rescue["title"])
    status = (
        ":green[:material/check_circle: Completed]"
        if rescue["status"] == RescueStatus.COMPLETED.value
        else ":orange[:material/pending: Open]"
    )
    st.markdown(f"{status} · Posted by {rescue['owner']} · {rescue['difficulty']} repair")
    st.write(rescue["description"])
    st.markdown(f"**Repair direction**  \n{rescue['next_step']}")
    st.caption(f"Estimated waste avoided if repaired: {rescue['estimated_waste_kg']:g} kg")
    show_listing_image(rescue, full=True)
    contributions = rescue.get("contributions", [])
    with st.expander(
        f"Community contributions ({len(contributions)})", expanded=bool(contributions)
    ):
        if contributions:
            for contribution in contributions:
                st.write(f"**{contribution['player']}** — {contribution['message']}")
        else:
            st.caption("No contributions yet.")
    if rescue["owner"] == st.session_state.current_player:
        owner_actions(rescue)
    elif rescue["status"] == RescueStatus.OPEN.value:
        contribution_form(rescue)
    else:
        st.success(f"Resolved as {rescue['outcome']}")
        if rescue.get("solvers"):
            st.write(f"Solved by: {', '.join(rescue['solvers'])}")


def card_grid(rescues: list[dict], context: str, empty_message: str) -> None:
    if not rescues:
        st.caption(f":material/inbox: {empty_message}")
        return
    for index in range(0, len(rescues), 2):
        columns = st.columns(2, gap="medium")
        for column, rescue in zip(columns, rescues[index : index + 2], strict=False):
            with column:
                listing_card(rescue, context)


def impact_summary(
    waste_avoided: float,
    secondary_metrics: list[tuple[str, str]],
) -> None:
    items = "".join(
        (
            '<div class="metric-item">'
            f'<div class="metric-label">{escape(label)}</div>'
            f'<div class="metric-value">{escape(value)}</div>'
            "</div>"
        )
        for label, value in secondary_metrics
    )
    st.markdown(
        (
            '<div class="impact-summary">'
            f'<div class="impact-value"><strong>{waste_avoided:.1f} kg</strong> '
            "waste avoided</div>"
            f'<div class="metric-grid">{items}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def dashboard_page() -> None:
    player = st.session_state.current_player
    stats = st.session_state.player_stats[player]
    contributed = [
        rescue
        for rescue in st.session_state.rescues
        if any(item["player"] == player for item in rescue.get("contributions", []))
    ]
    solved = repairs_helped_by(st.session_state.rescues, player)
    completed_positive = {
        rescue["id"]: rescue
        for rescue in [*contributed, *solved]
        if rescue["status"] == RescueStatus.COMPLETED.value
        and rescue.get("outcome") == RescueOutcome.REPAIR.value
    }
    waste_avoided = sum(item["estimated_waste_kg"] for item in completed_positive.values())

    with st.container(key="dashboard-intro", gap=None):
        st.title(f"Welcome back, {player}")
        st.caption("Your repair history, real-world impact, and community standing in one place.")
    show_flash()
    item_word = "item" if len(completed_positive) == 1 else "items"
    st.write(
        f"You’ve helped keep {len(completed_positive)} {item_word} in use and avoided "
        f"{waste_avoided:g} kg of waste."
    )
    impact_summary(
        waste_avoided,
        [
            ("XP", str(stats["xp"])),
            ("Current streak", f"{streak_length(stats['activity_dates'])} days"),
            ("Items helped", str(len(completed_positive))),
        ],
    )

    st.subheader("Your activity")
    contributed_tab, solved_tab = st.tabs(
        [f"Contributed to ({len(contributed)})", f"Solved ({len(solved)})"]
    )
    with contributed_tab:
        card_grid(contributed, "dashboard-contributed", "You have not contributed to an item yet.")
    with solved_tab:
        card_grid(
            solved,
            "dashboard-solved",
            "No solved items yet. Get recognised by an owner to see one here.",
        )

    st.subheader("Campus contributors")
    leaderboard = sorted(
        st.session_state.player_stats.items(), key=lambda item: item[1]["xp"], reverse=True
    )
    user_rank = next(rank for rank, (name, _) in enumerate(leaderboard, start=1) if name == player)
    st.caption(f"You are currently ranked #{user_rank} of {len(leaderboard)} players.")
    for rank, (name, player_stats) in enumerate(leaderboard[:5], start=1):
        rank_label = str(rank)
        current_player_badge = (
            '<span class="leaderboard-you">You</span>' if name == player else ""
        )
        row_classes = ["leaderboard-card"]
        if rank == 1:
            row_classes.append("leader")
        if name == player:
            row_classes.append("current")
        streak = streak_length(player_stats["activity_dates"])
        st.markdown(
            f"""
            <div class="{' '.join(row_classes)}">
                <div class="leaderboard-rank">{rank_label}</div>
                <div class="leaderboard-person">
                    <div class="leaderboard-name">{escape(name)}{current_player_badge}</div>
                    <div class="leaderboard-streak">{streak}-day streak</div>
                </div>
                <div class="leaderboard-score">{player_stats['xp']}<span>XP</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.caption(
        f"Contribution: {CONTRIBUTOR_XP} XP · Resolving: {COMPLETER_XP} XP · Solver: {SOLVER_XP} XP"
    )


def listings_page() -> None:
    player = st.session_state.current_player
    st.title("Listings")
    st.caption("Browse active repair requests or manage every item you have posted.")
    show_flash()
    community_tab, mine_tab = st.tabs(["Community listings", "My listings"])
    with community_tab:
        community = [
            rescue
            for rescue in st.session_state.rescues
            if rescue["status"] == RescueStatus.OPEN.value and rescue["owner"] != player
        ]
        card_grid(community, "community", "No community listings are open right now.")
    with mine_tab:
        mine = [rescue for rescue in st.session_state.rescues if rescue["owner"] == player]
        active = [rescue for rescue in mine if rescue["status"] == RescueStatus.OPEN.value]
        resolved = [rescue for rescue in mine if rescue["status"] == RescueStatus.COMPLETED.value]
        st.caption(f"{len(active)} active · {len(resolved)} resolved")
        card_grid(mine, "mine", "You have not posted any listings yet. Start from Report.")


def analysis_panel(analysis: RescueAnalysis) -> None:
    with st.container(key="assessment-panel"):
        st.caption("2 · Review assessment · Private until you post")
        st.subheader(analysis.rescue_title)
        details, stats = st.columns([2, 1])
        with details:
            st.write(analysis.reason)
            st.markdown(f"**Recommended next step**  \n{analysis.suggested_next_step}")
        with stats:
            st.metric("Difficulty", analysis.difficulty.value)
            st.metric("Waste potentially saved", f"{analysis.estimated_waste_kg:g} kg")


def report_page() -> None:
    st.title("Report a broken item")
    st.caption(
        "Share an item before replacing or disposing of it. The community can help repair it."
    )
    show_flash()
    st.caption(
        "AI analysis is ready."
        if ai_available()
        else "Demo mode: add an OpenAI key for photo analysis."
    )
    with st.container(key="report-panel"):
        st.subheader("1 · Describe it")
        with st.form("analyse-rescue", border=False):
            image = st.file_uploader(
                "Photo of the item", type=["jpg", "jpeg", "png", "webp"]
            )
            description = st.text_area(
                "What happened?",
                placeholder="My desk fan hums, but the blades no longer turn.",
            )
            generated = st.form_submit_button(
                "Assess item", type="primary", icon=":material/auto_awesome:"
            )
    if generated:
        if not description.strip():
            st.warning("Add a short description first.")
        else:
            try:
                with st.spinner("Assessing whether a repair attempt makes sense…"):
                    st.session_state.analysis = analyze_item(
                        description.strip(),
                        image.getvalue() if image else None,
                        image.type if image else "image/jpeg",
                    ).model_dump(mode="json")
                    st.session_state.analysis_description = description.strip()
                    st.session_state.analysis_image_bytes = image.getvalue() if image else None
                    st.session_state.analysis_image_mime = image.type if image else None
            except Exception as exc:
                st.error(f"AI analysis failed: {exc}")
    if st.session_state.analysis:
        analysis = RescueAnalysis.model_validate(st.session_state.analysis)
        analysis_panel(analysis)
        if st.button("Post repair request", type="primary", icon=":material/publish:"):
            try:
                create_rescue(
                    analysis,
                    st.session_state.analysis_description,
                    st.session_state.analysis_image_bytes,
                    st.session_state.analysis_image_mime,
                )
                st.session_state.analysis = None
                st.session_state.analysis_description = ""
                st.session_state.analysis_image_bytes = None
                st.session_state.analysis_image_mime = None
                st.session_state.flash = "Your repair request is now live in My listings."
                st.session_state.page = "Listings"
                st.rerun()
            except db.PersistenceError as exc:
                st.error(str(exc))


initialise_state()
st.session_state.setdefault("page", "Dashboard")
top_bar()
st.space("small")

if st.session_state.page == "Dashboard":
    dashboard_page()
elif st.session_state.page == "Listings":
    listings_page()
else:
    report_page()
