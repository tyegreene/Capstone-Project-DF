# app.py

import streamlit as st
import betfairlightweight
from betfairlightweight import filters
import os
from datetime import datetime, timezone, date, timedelta
import json
import pandas as pd

# ------------------------------
# Page configuration
# ------------------------------
st.set_page_config(
    page_title="GB & IRE Horse Racing Analytics",
    page_icon="🐎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ------------------------------
# Initialize session state
# ------------------------------
if 'page' not in st.session_state:
    st.session_state.page = 'Home'

if 'selected_date' not in st.session_state:
    st.session_state.selected_date = date.today()

# ------------------------------
# Sidebar Navigation
# ------------------------------
with st.sidebar:
    st.title("🐎 Navigation")
    st.divider()

    # Date filter section
    st.subheader("📅 Date Filter")
    selected_date = st.date_input(
        "Select Date",
        value=st.session_state.selected_date,
        min_value=date.today() - timedelta(days=30),
        max_value=date.today() + timedelta(days=30)
    )

    # Update session state when date input changes
    if selected_date != st.session_state.selected_date:
        st.session_state.selected_date = selected_date
        st.rerun()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Today", use_container_width=True):
            st.session_state.selected_date = date.today()
            st.rerun()
    with col2:
        if st.button("Tomorrow", use_container_width=True):
            st.session_state.selected_date = date.today() + timedelta(days=1)
            st.rerun()

    st.divider()

    nav_pages = [
        ("🏠", "Home", "Home"),
        ("📅", "Upcoming Races", "Upcoming"),
        ("🏁", "Finished Races", "Finished"),
        ("💰", "Bet Simulator", "Bet Simulator")
    ]
    
    for icon, label, page_name in nav_pages:
        if st.button(f"{icon} {label}", use_container_width=True,
                     type="primary" if st.session_state.page == page_name else "secondary"):
            st.session_state.page = page_name
            st.rerun()

    st.divider()
    st.caption("GB & IRE Horse Racing Analytics")

# ------------------------------
# Betfair Client
# ------------------------------
@st.cache_resource
def init_betfair_client():
    """Initialize Betfair API client"""
    with open("credentials.json") as f:
        cred = json.load(f)

    USERNAME = cred["username"]
    PASSWORD = cred["password"]
    APP_KEY = cred["app_key"]

    crt_path = os.path.abspath("certs/client-2048.crt")
    key_path = os.path.abspath("certs/client-2048.key")

    trading = betfairlightweight.APIClient(
        username=USERNAME,
        password=PASSWORD,
        app_key=APP_KEY,
        cert_files=(crt_path, key_path)
    )

    try:
        trading.login()
        return trading, None
    except Exception as e:
        return None, str(e)

# ------------------------------
# Helper: Create date range for market filter
# ------------------------------
def get_date_range(selected_date):
    """Get start and end datetime for a given date"""
    start_dt = datetime.combine(selected_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(selected_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    return start_dt, end_dt

# ------------------------------
# Helper: Create market filter
# ------------------------------
def create_market_filter(selected_date, market_ids=None):
    """Create market filter for GB horse racing WIN markets"""
    start_dt, end_dt = get_date_range(selected_date)
    filter_params = {
        'event_type_ids': ['7'],
        'market_type_codes': ['WIN'],
        'market_countries': ['GB'],
        'market_start_time': {
            "from": start_dt.isoformat(),
            "to": end_dt.isoformat()
        }
    }
    if market_ids:
        filter_params['market_ids'] = market_ids
    return filters.market_filter(**filter_params)

# ------------------------------
# Fetch Markets (Upcoming & Finished)
# ------------------------------
@st.cache_data(ttl=60)
def fetch_markets(_trading, selected_date):
    """Fetch all UK WIN markets for the selected date"""
    now = datetime.now(timezone.utc)
    try:
        market_filter_obj = create_market_filter(selected_date)
        markets = _trading.betting.list_market_catalogue(
            filter=market_filter_obj,
            max_results=500,
            market_projection=['EVENT', 'MARKET_START_TIME']
        )

        upcoming, finished = [], []
        for m in markets:
            event_time = m.market_start_time
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            (upcoming if event_time > now else finished).append(m)

        upcoming.sort(key=lambda x: x.market_start_time)
        finished.sort(key=lambda x: x.market_start_time)
        return upcoming, finished, None
    except Exception as e:
        return [], [], str(e)

# ------------------------------
# Fetch Market Details with Runners
# ------------------------------
@st.cache_data(ttl=60)
def fetch_market_details(_trading, market_id, selected_date):
    """Fetch detailed market information with runners"""
    try:
        market_filter_obj = create_market_filter(selected_date, market_ids=[market_id])
        markets = _trading.betting.list_market_catalogue(
            filter=market_filter_obj,
            max_results=1,
            market_projection=['EVENT', 'MARKET_START_TIME', 'RUNNER_DESCRIPTION', 'RUNNER_METADATA']
        )
        return (markets[0], None) if markets else (None, "Market not found")
    except Exception as e:
        return None, str(e)

# ------------------------------
# Fetch Market Book (for winner/position info)
# ------------------------------
@st.cache_data(ttl=60)
def fetch_market_book(_trading, market_id):
    """Fetch market book to get winner/position information"""
    try:
        market_books = _trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection=None
        )
        
        if market_books:
            return market_books[0], None
        return None, "Market book not found"
    
    except Exception as e:
        return None, str(e)

# ------------------------------
# Fetch Market Book with Odds (for bet simulator)
# ------------------------------
@st.cache_data(ttl=30)
def fetch_market_book_with_odds(_trading, market_id):
    """Fetch market book with odds for bet simulator"""
    try:
        market_books = _trading.betting.list_market_book(
            market_ids=[market_id],
            price_projection={'priceData': ['EX_BEST_OFFERS']}
        )
        
        if market_books:
            market_book = market_books[0]
            # Build odds map: selection_id -> best back odds
            odds_map = {}
            for runner in market_book.runners:
                best_back_odds = None
                if hasattr(runner, 'ex') and hasattr(runner.ex, 'available_to_back') and runner.ex.available_to_back:
                    best_back_odds = runner.ex.available_to_back[0].price
                odds_map[runner.selection_id] = best_back_odds
            return market_book, odds_map, None
        return None, {}, "Market book not found"
    
    except Exception as e:
        return None, {}, str(e)

# ------------------------------
# Initialize client
# ------------------------------
trading, login_error = init_betfair_client()
if login_error:
    st.error(f"❌ Login failed: {login_error}")
    st.stop()

# ------------------------------
# Helper: Get course name
# ------------------------------
def get_course(market):
    if hasattr(market, "event") and market.event:
        if hasattr(market.event, "venue") and market.event.venue:
            return market.event.venue
        if hasattr(market.event, "name") and market.event.name:
            return market.event.name
    return "Unknown Course"

# ------------------------------
# Helper: Extract runner metadata
# ------------------------------
def get_runner_info(runner):
    """Extract horse information from runner object"""
    metadata = runner.metadata or {}
    return {
        'name': runner.runner_name,
        'cloth_number': metadata.get("CLOTH_NUMBER") or "N/A",
        'jockey': metadata.get("JOCKEY_NAME") or "N/A",
        'trainer': metadata.get("TRAINER_NAME") or "N/A",
        'selection_id': runner.selection_id
    }

# ------------------------------
# Helper: Format race display string
# ------------------------------
def format_race_display(market):
    """Format race for display: time - course - race name"""
    start_local = market.market_start_time.astimezone()
    time_str = start_local.strftime("%H:%M")
    course = get_course(market)
    return f"{time_str}  -  {course}  -  {market.market_name}"

# ------------------------------
# Helper: Format date for display
# ------------------------------
def format_date_display(selected_date):
    """Format date for display"""
    return selected_date.strftime('%B %d, %Y')


# ------------------------------
# Page Routing
# ------------------------------
if st.session_state.page == 'Home':
    st.title("🐎 Welcome to GB & IRE Horse Racing Analytics")
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style='text-align: center; padding: 2rem;'>
            <h2>Your Gateway to GB & IRE Horse Racing Data</h2>
            <p style='font-size: 1.2em; color: #666; margin: 2rem 0;'>
                Explore upcoming races, view results, and analyze horse racing data 
                from the Betfair API.
            </p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("🚀 View Upcoming Races", type="primary", use_container_width=True):
            st.session_state.page = 'Upcoming'
            st.rerun()

        st.success("✅ Connected to Betfair API")

        upcoming, finished, err = fetch_markets(trading, st.session_state.selected_date)
        if not err:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Upcoming Races", len(upcoming))
            with col2:
                st.metric("Finished Races", len(finished))

# ------------------------------
# Upcoming Races Page
# ------------------------------
elif st.session_state.page == 'Upcoming':
    st.title("📅 Upcoming Races")
    st.markdown(f"**Races for: {format_date_display(st.session_state.selected_date)}**")
    st.markdown("---")

    upcoming, finished, err = fetch_markets(trading, st.session_state.selected_date)

    if err:
        st.error(err)
    elif upcoming:
        st.write(f"**Total upcoming races: {len(upcoming)}**")
        st.divider()
        for m in upcoming:
            with st.expander(format_race_display(m), expanded=False):
                market_details, detail_err = fetch_market_details(trading, m.market_id, st.session_state.selected_date)
                market_book, odds_map, _ = fetch_market_book_with_odds(trading, m.market_id)
                
                if detail_err:
                    st.warning(f"Could not load horse details: {detail_err}")
                elif market_details and hasattr(market_details, 'runners') and market_details.runners:
                    # Build runner map and identify favorite (lowest back odds, excluding non-runners)
                    book_runner_map = {}
                    if market_book and hasattr(market_book, 'runners'):
                        book_runner_map = {r.selection_id: r for r in market_book.runners}
                    
                    # Find favorite by checking lowest odds (excluding non-runners)
                    favorite_selection_id = None
                    lowest_odds = float('inf')
                    for runner in market_details.runners:
                        # Skip non-runners when finding favorite
                        book_runner = book_runner_map.get(runner.selection_id)
                        is_non_runner = (book_runner and hasattr(book_runner, 'status') and 
                                        book_runner.status == 'REMOVED')
                        if not is_non_runner:
                            odds = odds_map.get(runner.selection_id)
                            if odds is not None and odds < lowest_odds:
                                lowest_odds = odds
                                favorite_selection_id = runner.selection_id
                    
                    for runner in market_details.runners:
                        info = get_runner_info(runner)
                        book_runner = book_runner_map.get(info['selection_id'])
                        is_non_runner = (book_runner and hasattr(book_runner, 'status') and 
                                        book_runner.status == 'REMOVED')
                        flame_emoji = " 🔥" if info['selection_id'] == favorite_selection_id else ""
                        nr_label = " (NR)" if is_non_runner else ""
                        horse_label = f"**{info['name']}**{flame_emoji} — Cloth #{info['cloth_number']}{nr_label}"
                        if info['jockey'] != "N/A":
                            horse_label += f"  \n*{info['jockey']}*"
                        
                        with st.expander(horse_label, expanded=False):
                            st.markdown('[View more](https://www.timeform.com/horse-racing)')
                else:
                    st.info("No runner information available for this race.")
    else:
        st.info("No upcoming races found.")

# ------------------------------
# Finished Races Page
# ------------------------------
elif st.session_state.page == 'Finished':
    st.title("🏁 Finished Races / Results")
    st.markdown(f"**Showing races for: {format_date_display(st.session_state.selected_date)}**")
    st.markdown("---")
    
    upcoming, finished, fetch_error = fetch_markets(trading, st.session_state.selected_date)
    
    if fetch_error:
        st.error(f"Error fetching events: {fetch_error}")
    elif finished:
        st.write(f"**Total finished races: {len(finished)}**")
        st.divider()
        for m in finished:
            with st.expander(format_race_display(m), expanded=False):
                market_details, detail_err = fetch_market_details(trading, m.market_id, st.session_state.selected_date)
                market_book, book_err = fetch_market_book(trading, m.market_id)
                
                if detail_err:
                    st.warning(f"Could not load horse details: {detail_err}")
                elif market_details and hasattr(market_details, 'runners') and market_details.runners:
                    # Build runner map and identify winner using multiple fallback methods
                    book_runner_map = {}
                    winner_selection_id = None
                    
                    if market_book and hasattr(market_book, 'runners') and market_book.runners:
                        for book_runner in market_book.runners:
                            book_runner_map[book_runner.selection_id] = book_runner
                            # Try position attribute first
                            if hasattr(book_runner, 'position') and book_runner.position == 1:
                                winner_selection_id = book_runner.selection_id
                            # Fallback to placement attribute
                            elif hasattr(book_runner, 'placement') and book_runner.placement == 1:
                                winner_selection_id = book_runner.selection_id
                            # Final fallback: if market closed and only one active runner
                            elif (hasattr(market_book, 'status') and market_book.status == 'CLOSED' and
                                  hasattr(book_runner, 'status') and book_runner.status == 'ACTIVE' and
                                  winner_selection_id is None):
                                active_runners = [r for r in market_book.runners 
                                                 if hasattr(r, 'status') and r.status == 'ACTIVE' and
                                                 not (hasattr(r, 'position') and r.position is not None and r.position != 1)]
                                if len(active_runners) == 1:
                                    winner_selection_id = book_runner.selection_id
                    
                    for runner in market_details.runners:
                        info = get_runner_info(runner)
                        book_runner = book_runner_map.get(info['selection_id'])
                        is_non_runner = (book_runner and hasattr(book_runner, 'status') and 
                                        book_runner.status == 'REMOVED')
                        is_winner = (winner_selection_id is not None and 
                                   info['selection_id'] == winner_selection_id)
                        
                        status_text = " 🥇 **Winner**" if is_winner else (" **NR**" if is_non_runner else "")
                        horse_display = f"**{info['name']}**{status_text} — Cloth #{info['cloth_number']}"
                        
                        if info['jockey'] != "N/A":
                            st.markdown(f"{horse_display}  \n*{info['jockey']}*")
                        else:
                            st.markdown(horse_display)
                else:
                    st.info("No runner information available for this race.")
        
        # Link to Timeform results at bottom of page
        st.divider()
        st.markdown('[See results](https://www.timeform.com/horse-racing)')
    else:
        st.info("No finished races found.")

# ------------------------------
# Bet Simulator Page
# ------------------------------
elif st.session_state.page == 'Bet Simulator':
    st.title("💰 Bet Simulator")
    st.markdown("---")
    
    # Fetch upcoming races for bet simulation
    upcoming, finished, err = fetch_markets(trading, st.session_state.selected_date)
    
    if err:
        st.error(f"Error fetching races: {err}")
    elif not upcoming:
        st.info("No upcoming races available for bet simulation.")
    else:
        # Race selection dropdown
        race_options = {format_race_display(m): m for m in upcoming}
        selected_race_key = st.selectbox("Select Race", list(race_options.keys()))
        selected_market = race_options[selected_race_key]
        
        # Fetch market details and current odds
        market_details, detail_err = fetch_market_details(trading, selected_market.market_id, st.session_state.selected_date)
        market_book, odds_map, book_err = fetch_market_book_with_odds(trading, selected_market.market_id)
        
        if detail_err:
            st.error(f"Error loading race details: {detail_err}")
        elif not market_details or not hasattr(market_details, 'runners') or not market_details.runners:
            st.info("No runners available for this race.")
        else:
            # Build odds comparison chart data
            horses_data = []
            for runner in market_details.runners:
                info = get_runner_info(runner)
                odds = odds_map.get(info['selection_id'])
                if odds is not None:
                    horses_data.append({
                        'Horse': f"{info['name']} (#{info['cloth_number']})",
                        'Odds': odds
                    })
            
            # Display collapsible odds comparison chart
            if horses_data:
                df_odds = pd.DataFrame(horses_data)
                df_odds = df_odds.sort_values('Odds', ascending=True)
                
                with st.expander("📊 Odds Comparison Chart", expanded=False):
                    st.bar_chart(df_odds.set_index('Horse'), use_container_width=True)
                    st.caption("Lower odds indicate higher probability of winning (favorite)")
            
            st.divider()
            
            # Horse selection dropdown with odds display
            horse_options = {}
            for runner in market_details.runners:
                info = get_runner_info(runner)
                odds = odds_map.get(info['selection_id'])
                odds_display = f"{odds:.2f}" if odds else "N/A"
                horse_key = f"{info['name']} (Cloth #{info['cloth_number']}) - Odds: {odds_display}"
                horse_options[horse_key] = (runner, odds)
            
            selected_horse_key = st.selectbox("Select Horse", list(horse_options.keys()))
            selected_runner, selected_odds = horse_options[selected_horse_key]
            
            if selected_odds is None:
                st.warning("⚠️ Odds not available for this horse. Please select another horse.")
            else:
                st.divider()
                
                # Bet input fields (stake, bet type, odds)
                col1, col2 = st.columns(2)
                with col1:
                    stake = st.number_input("Stake (£)", min_value=0.01, value=10.0, step=0.01, format="%.2f")
                    bet_type = st.selectbox("Bet Type", ["Win", "Each Way", "Lay"])
                
                with col2:
                    odds_input = st.number_input("Odds (Decimal)", min_value=1.01, value=float(selected_odds), step=0.01, format="%.2f")
                    if bet_type == "Each Way":
                        ew_places = st.selectbox("Each Way Places", ["1/4 (4 places)", "1/5 (5 places)", "1/6 (6 places)"], index=0)
                        place_factor = {"1/4 (4 places)": 4, "1/5 (5 places)": 5, "1/6 (6 places)": 6}[ew_places]
                
                st.divider()
                
                # Bet calculation and display
                st.subheader("📊 Bet Calculations")
                
                if bet_type == "Win":
                    profit = stake * (odds_input - 1)
                    total_return = stake + profit
                    roi = (profit / stake) * 100
                    implied_prob = (1 / odds_input) * 100
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Potential Profit", f"£{profit:.2f}")
                    with col2:
                        st.metric("Total Return", f"£{total_return:.2f}")
                    with col3:
                        st.metric("ROI", f"{roi:.1f}%")
                    with col4:
                        st.metric("Implied Probability", f"{implied_prob:.1f}%")
                
                elif bet_type == "Each Way":
                    win_stake = stake / 2
                    place_stake = stake / 2
                    place_odds = odds_input / place_factor
                    
                    win_profit = win_stake * (odds_input - 1)
                    place_profit = place_stake * (place_odds - 1)
                    total_win_return = win_stake + win_profit
                    total_place_return = place_stake + place_profit
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Win Profit", f"£{win_profit:.2f}")
                    with col2:
                        st.metric("Place Profit", f"£{place_profit:.2f}")
                    with col3:
                        st.metric("Total Win Return", f"£{total_win_return:.2f}")
                    with col4:
                        st.metric("Total Place Return", f"£{total_place_return:.2f}")
                    
                    st.info(f"**Each Way Breakdown:** £{win_stake:.2f} on Win @ {odds_input:.2f}, £{place_stake:.2f} on Place @ {place_odds:.2f}")
                
                elif bet_type == "Lay":
                    liability = stake * (odds_input - 1)
                    profit_if_loses = stake
                    implied_prob = (1 / odds_input) * 100
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Liability", f"£{liability:.2f}")
                    with col2:
                        st.metric("Profit if Loses", f"£{profit_if_loses:.2f}")
                    with col3:
                        st.metric("Total Risk", f"£{liability:.2f}")
                    with col4:
                        st.metric("Implied Probability", f"{implied_prob:.1f}%")
                
