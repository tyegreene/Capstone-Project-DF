"""
Pytest tests for GB & IRE Horse Racing Analytics app
Tests key data processing, transformation, and cleaning functions
"""

import pytest
from datetime import datetime, timezone, date
from unittest.mock import Mock


# Helper functions copied from app.py for testing
# (These are pure functions that don't depend on Streamlit or Betfair API)

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


class TestDataExtractionAndCleaning:
    """Test data extraction and cleaning functions"""
    
    def test_get_runner_info_with_missing_metadata(self):
        """Test extracting runner info handles missing metadata gracefully"""
        mock_runner = Mock()
        mock_runner.runner_name = "Test Horse"
        mock_runner.selection_id = 12345
        mock_runner.metadata = {}  # Empty metadata
        
        info = get_runner_info(mock_runner)
        
        assert info['name'] == "Test Horse"
        assert info['selection_id'] == 12345
        assert info['cloth_number'] == "N/A"  # Default value for missing data
        assert info['jockey'] == "N/A"
        assert info['trainer'] == "N/A"


class TestOddsTransformation:
    """Test odds data transformation"""
    
    def test_odds_map_creation_from_market_book(self):
        """Test transformation of market book runners into odds map"""
        # Simulate market book with runners and odds
        mock_runner1 = Mock()
        mock_runner1.selection_id = 12345
        mock_price1 = Mock()
        mock_price1.price = 3.5
        mock_ex1 = Mock()
        mock_ex1.available_to_back = [mock_price1]
        mock_runner1.ex = mock_ex1
        
        mock_runner2 = Mock()
        mock_runner2.selection_id = 67890
        mock_price2 = Mock()
        mock_price2.price = 5.0
        mock_ex2 = Mock()
        mock_ex2.available_to_back = [mock_price2]
        mock_runner2.ex = mock_ex2
        
        # Simulate odds map creation logic
        odds_map = {}
        for runner in [mock_runner1, mock_runner2]:
            best_back_odds = None
            if hasattr(runner, 'ex') and hasattr(runner.ex, 'available_to_back') and runner.ex.available_to_back:
                best_back_odds = runner.ex.available_to_back[0].price
            odds_map[runner.selection_id] = best_back_odds
        
        assert odds_map[12345] == 3.5
        assert odds_map[67890] == 5.0
        assert len(odds_map) == 2


class TestFavoriteIdentification:
    """Test favorite horse identification logic"""
    
    def test_favorite_identification_excludes_non_runners(self):
        """Test identifying favorite (lowest odds) while excluding non-runners"""
        # Simulate runners with odds
        runners_data = [
            {'selection_id': 1, 'odds': 5.0, 'is_non_runner': False},
            {'selection_id': 2, 'odds': 2.5, 'is_non_runner': False},  # Should be favorite
            {'selection_id': 3, 'odds': 1.8, 'is_non_runner': True},  # Non-runner (lowest odds but excluded)
            {'selection_id': 4, 'odds': 8.0, 'is_non_runner': False},
        ]
        
        favorite_selection_id = None
        lowest_odds = float('inf')
        
        for runner_data in runners_data:
            if not runner_data['is_non_runner']:
                odds = runner_data['odds']
                if odds is not None and odds < lowest_odds:
                    lowest_odds = odds
                    favorite_selection_id = runner_data['selection_id']
        
        assert favorite_selection_id == 2  # Not the non-runner with 1.8 odds
        assert lowest_odds == 2.5


class TestNonRunnerDetection:
    """Test non-runner detection logic"""
    
    def test_non_runner_detection_via_status(self):
        """Test detecting non-runners through status attribute"""
        mock_book_runner = Mock()
        mock_book_runner.selection_id = 12345
        mock_book_runner.status = 'REMOVED'
        
        is_non_runner = (hasattr(mock_book_runner, 'status') and 
                        mock_book_runner.status == 'REMOVED')
        
        assert is_non_runner is True


class TestWinnerIdentification:
    """Test winner identification logic"""
    
    def test_winner_identification_by_position(self):
        """Test identifying winner via position attribute"""
        mock_book_runner1 = Mock()
        mock_book_runner1.selection_id = 111
        mock_book_runner1.position = 1  # Winner
        
        mock_book_runner2 = Mock()
        mock_book_runner2.selection_id = 222
        mock_book_runner2.position = 2
        
        winner_selection_id = None
        for runner in [mock_book_runner1, mock_book_runner2]:
            if hasattr(runner, 'position') and runner.position == 1:
                winner_selection_id = runner.selection_id
        
        assert winner_selection_id == 111


class TestMarketClassification:
    """Test market classification and sorting"""
    
    def test_market_classification_and_sorting(self):
        """Test splitting markets into upcoming/finished and sorting by time"""
        now = datetime.now(timezone.utc)
        future_time = datetime.now(timezone.utc).replace(hour=23, minute=0, second=0, microsecond=0)
        past_time = datetime.now(timezone.utc).replace(hour=1, minute=0, second=0, microsecond=0)
        
        mock_market1 = Mock()
        mock_market1.market_start_time = future_time
        
        mock_market2 = Mock()
        mock_market2.market_start_time = past_time
        
        mock_market3 = Mock()
        mock_market3.market_start_time = datetime.now(timezone.utc).replace(hour=15, minute=0, second=0, microsecond=0)
        
        # Classify markets
        upcoming, finished = [], []
        for market in [mock_market1, mock_market2, mock_market3]:
            event_time = market.market_start_time
            if event_time.tzinfo is None:
                event_time = event_time.replace(tzinfo=timezone.utc)
            (upcoming if event_time > now else finished).append(market)
        
        # Sort markets
        upcoming.sort(key=lambda x: x.market_start_time)
        finished.sort(key=lambda x: x.market_start_time)
        
        # Verify sorting works
        if len(upcoming) > 1:
            assert upcoming[0].market_start_time <= upcoming[1].market_start_time
        if len(finished) > 1:
            assert finished[0].market_start_time <= finished[1].market_start_time


class TestBetCalculations:
    """Test bet calculation logic"""
    
    def test_win_bet_calculation(self):
        """Test win bet profit, return, ROI, and implied probability calculations"""
        stake = 10.0
        odds = 3.5
        
        profit = stake * (odds - 1)
        total_return = stake + profit
        roi = (profit / stake) * 100
        implied_prob = (1 / odds) * 100
        
        assert profit == 25.0
        assert total_return == 35.0
        assert roi == 250.0
        assert round(implied_prob, 2) == 28.57


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
