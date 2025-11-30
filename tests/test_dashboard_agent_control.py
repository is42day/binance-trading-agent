"""
Tests for Dashboard Agent Control Functionality
Tests the automation page agent start/stop/restart functionality
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from binance_trade_agent.dashboard.utils.data_fetch import (
    get_agent_state,
    restart_agent,
    start_agent,
    stop_agent,
)


@pytest.fixture
def reset_agent_state():
    """Reset agent state before each test"""
    from binance_trade_agent.dashboard.utils import data_fetch
    
    data_fetch._agent_state = {
        "is_running": False,
        "start_time": None,
        "stop_time": None,
        "task": None,
        "trading_loop": None,
    }
    yield
    # Cleanup after test
    data_fetch._agent_state = {
        "is_running": False,
        "start_time": None,
        "stop_time": None,
        "task": None,
        "trading_loop": None,
    }


class TestAgentStateManagement:
    """Test agent state management functions"""
    
    def test_initial_agent_state(self, reset_agent_state):
        """Test that agent starts in stopped state"""
        state = get_agent_state()
        assert state["is_running"] is False
        assert state["start_time"] is None
        assert state["stop_time"] is None
        assert state["task"] is None
        assert state["trading_loop"] is None
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_start_agent_creates_trading_loop(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that starting agent creates trading loop and task"""
        # Setup mocks
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        
        mock_trading_loop = MagicMock()
        mock_trading_loop_class.return_value = mock_trading_loop
        
        # Start agent
        result = start_agent(symbols=["BTCUSDT"], interval=120, strategy="combined_default")
        
        # Verify result
        assert result["success"] is True
        assert "started successfully" in result["message"]
        
        # Verify trading loop created with correct parameters
        mock_trading_loop_class.assert_called_once_with(
            symbols=["BTCUSDT"],
            trade_interval_seconds=120,
            duration_minutes=0,
            strategy_name="combined_default",
        )
        
        # Verify task created
        mock_loop.create_task.assert_called_once()
        
        # Verify state updated
        state = get_agent_state()
        assert state["is_running"] is True
        assert state["start_time"] is not None
        assert state["stop_time"] is None
        assert state["task"] == mock_task
        assert state["trading_loop"] == mock_trading_loop
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_start_agent_when_already_running(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that starting agent when already running returns error"""
        # Setup mock for first start
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        mock_trading_loop_class.return_value = MagicMock()
        
        # Start agent first time
        result1 = start_agent()
        assert result1["success"] is True
        
        # Try to start again
        result2 = start_agent()
        assert result2["success"] is False
        assert "already running" in result2["message"]
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_stop_agent_sets_stop_flag_and_cancels_task(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that stopping agent sets stop flag and cancels task"""
        # Setup and start agent
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        
        mock_trading_loop = MagicMock()
        mock_trading_loop_class.return_value = mock_trading_loop
        
        start_agent()
        
        # Stop agent
        result = stop_agent()
        
        # Verify result
        assert result["success"] is True
        assert "stopped successfully" in result["message"]
        
        # Verify stop flag set
        assert mock_trading_loop.stop_flag is True
        
        # Verify task cancelled
        mock_task.cancel.assert_called_once()
        
        # Verify state updated
        state = get_agent_state()
        assert state["is_running"] is False
        assert state["stop_time"] is not None
        assert state["task"] is None
        assert state["trading_loop"] is None
    
    def test_stop_agent_when_not_running(self, reset_agent_state):
        """Test that stopping agent when not running returns error"""
        result = stop_agent()
        assert result["success"] is False
        assert "not running" in result["message"]
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_restart_agent_stops_and_starts(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that restarting agent stops and then starts it"""
        # Setup mocks
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        mock_trading_loop_class.return_value = MagicMock()
        
        # Start then restart
        start_agent()
        result = restart_agent()
        
        # Verify success
        assert result["success"] is True
        assert "started successfully" in result["message"]
        
        # Verify agent is running after restart
        state = get_agent_state()
        assert state["is_running"] is True
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_restart_agent_when_not_running(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that restarting agent when not running just starts it"""
        # Setup mocks
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        mock_trading_loop_class.return_value = MagicMock()
        
        # Restart when not running
        result = restart_agent()
        
        # Verify success (should just start)
        assert result["success"] is True
        
        # Verify agent is running
        state = get_agent_state()
        assert state["is_running"] is True


class TestAgentControlWithDefaultParameters:
    """Test agent control with default parameters"""
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_start_agent_default_parameters(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test starting agent with default parameters"""
        # Setup mocks
        mock_loop = MagicMock()
        mock_loop.create_task.return_value = MagicMock()
        mock_get_loop.return_value = mock_loop
        mock_trading_loop_class.return_value = MagicMock()
        
        # Start with no parameters
        result = start_agent()
        
        # Verify defaults used
        mock_trading_loop_class.assert_called_once_with(
            symbols=["BTCUSDT", "ETHUSDT"],
            trade_interval_seconds=120,
            duration_minutes=0,
            strategy_name="combined_default",
        )
        
        assert result["success"] is True


class TestAgentControlErrorHandling:
    """Test error handling in agent control"""
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_start_agent_handles_exceptions(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that start_agent handles exceptions gracefully"""
        # Make it raise an exception
        mock_trading_loop_class.side_effect = Exception("Test error")
        
        # Try to start
        result = start_agent()
        
        # Verify error handled
        assert result["success"] is False
        assert "Failed to start agent" in result["message"]
        assert "Test error" in result["message"]
        
        # Verify state not changed
        state = get_agent_state()
        assert state["is_running"] is False
    
    @patch("binance_trade_agent.dashboard.utils.data_fetch.AutonomousTradingLoop")
    @patch("binance_trade_agent.dashboard.utils.data_fetch.asyncio.get_event_loop")
    def test_stop_agent_handles_exceptions(self, mock_get_loop, mock_trading_loop_class, reset_agent_state):
        """Test that stop_agent handles exceptions gracefully"""
        # Setup and start agent
        mock_loop = MagicMock()
        mock_task = MagicMock()
        mock_task.cancel.side_effect = Exception("Cancel error")
        mock_loop.create_task.return_value = mock_task
        mock_get_loop.return_value = mock_loop
        mock_trading_loop_class.return_value = MagicMock()
        
        start_agent()
        
        # Try to stop (will raise exception)
        result = stop_agent()
        
        # Verify error handled
        assert result["success"] is False
        assert "Failed to stop agent" in result["message"]
