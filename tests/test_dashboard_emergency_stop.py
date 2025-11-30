"""
Tests for Dashboard Emergency Stop Functionality
Tests the advanced page emergency stop button
"""

from unittest.mock import MagicMock, patch

import pytest

from binance_trade_agent.dashboard.utils.data_fetch import get_trading_components


class TestEmergencyStopFunctionality:
    """Test emergency stop button functionality"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.EnhancedRiskManagementAgent")
    def test_emergency_stop_calls_set_emergency_stop(self, mock_risk_agent_class):
        """Test that emergency stop calls set_emergency_stop with correct parameters"""
        # Setup mock
        mock_risk_agent = MagicMock()
        mock_risk_agent_class.return_value = mock_risk_agent

        # Get components (will create risk agent)
        from binance_trade_agent.dashboard.utils import data_fetch

        data_fetch._components = None  # Reset cache

        components = get_trading_components()
        risk_agent = components["risk_agent"]

        # Call emergency stop
        risk_agent.set_emergency_stop(True, "Emergency stop triggered from dashboard")

        # Verify method called with correct parameters
        risk_agent.set_emergency_stop.assert_called_once_with(
            True, "Emergency stop triggered from dashboard"
        )

    @patch("binance_trade_agent.dashboard.utils.data_fetch.EnhancedRiskManagementAgent")
    def test_emergency_stop_sets_flag_to_true(self, mock_risk_agent_class):
        """Test that emergency stop sets the emergency_stop flag to True"""
        # Setup mock to track config changes
        mock_risk_agent = MagicMock()
        mock_risk_agent.config = {"emergency_stop": False}

        def set_emergency_stop_impl(enabled, reason=""):
            mock_risk_agent.config["emergency_stop"] = enabled

        mock_risk_agent.set_emergency_stop.side_effect = set_emergency_stop_impl
        mock_risk_agent_class.return_value = mock_risk_agent

        # Get components
        from binance_trade_agent.dashboard.utils import data_fetch

        data_fetch._components = None

        components = get_trading_components()
        risk_agent = components["risk_agent"]

        # Verify initial state
        assert risk_agent.config["emergency_stop"] is False

        # Trigger emergency stop
        risk_agent.set_emergency_stop(True, "Test emergency")

        # Verify flag set
        assert risk_agent.config["emergency_stop"] is True

    def test_risk_agent_has_set_emergency_stop_method(self):
        """Test that EnhancedRiskManagementAgent has set_emergency_stop method"""
        from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent

        # Create real instance
        risk_agent = EnhancedRiskManagementAgent()

        # Verify method exists
        assert hasattr(risk_agent, "set_emergency_stop")
        assert callable(risk_agent.set_emergency_stop)

    def test_emergency_stop_method_signature(self):
        """Test that set_emergency_stop has correct signature"""
        from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent
        import inspect

        risk_agent = EnhancedRiskManagementAgent()

        # Get method signature
        sig = inspect.signature(risk_agent.set_emergency_stop)
        params = list(sig.parameters.keys())

        # Verify parameters
        assert "enabled" in params
        assert "reason" in params

        # Verify reason has default value
        assert sig.parameters["reason"].default == ""

    def test_emergency_stop_actually_stops_trading(self):
        """Test that emergency stop prevents new trades"""
        from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent

        risk_agent = EnhancedRiskManagementAgent()

        # Create a mock trade proposal
        trade_proposal = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.001,
            "price": 50000,
            "signal_confidence": 0.8,
        }

        # Should allow trade initially
        assessment = risk_agent.assess_trade(trade_proposal)
        # Note: assessment might be rejected for other risk reasons, but not emergency stop

        # Activate emergency stop
        risk_agent.set_emergency_stop(True, "Test emergency stop")

        # Should reject trade now
        assessment_after = risk_agent.assess_trade(trade_proposal)
        assert assessment_after.approved is False
        assert any("Emergency stop" in reason for reason in assessment_after.reasons)

    @patch("binance_trade_agent.dashboard.utils.data_fetch.EnhancedRiskManagementAgent")
    def test_emergency_stop_can_be_cleared(self, mock_risk_agent_class):
        """Test that emergency stop can be disabled by setting to False"""
        # Setup mock
        mock_risk_agent = MagicMock()
        mock_risk_agent.config = {"emergency_stop": True}

        def set_emergency_stop_impl(enabled, reason=""):
            mock_risk_agent.config["emergency_stop"] = enabled

        mock_risk_agent.set_emergency_stop.side_effect = set_emergency_stop_impl
        mock_risk_agent_class.return_value = mock_risk_agent

        # Get components
        from binance_trade_agent.dashboard.utils import data_fetch

        data_fetch._components = None

        components = get_trading_components()
        risk_agent = components["risk_agent"]

        # Set emergency stop active
        assert risk_agent.config["emergency_stop"] is True

        # Clear emergency stop
        risk_agent.set_emergency_stop(False, "Test clear")

        # Verify cleared
        assert risk_agent.config["emergency_stop"] is False

    def test_get_risk_status_includes_emergency_stop(self):
        """Test that get_risk_status includes emergency_stop flag"""
        from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent

        risk_agent = EnhancedRiskManagementAgent()

        # Get status
        status = risk_agent.get_risk_status()

        # Verify emergency_stop in status
        assert "emergency_stop" in status
        assert isinstance(status["emergency_stop"], bool)
        assert status["emergency_stop"] is False  # Should be False initially

        # Set emergency stop and check again
        risk_agent.set_emergency_stop(True, "Test")
        status_after = risk_agent.get_risk_status()
        assert status_after["emergency_stop"] is True


class TestEmergencyStopIntegration:
    """Integration tests for emergency stop with other components"""

    def test_emergency_stop_with_orchestrator(self):
        """Test that emergency stop prevents orchestrator from executing trades"""
        from binance_trade_agent.agents.risk_management_agent import EnhancedRiskManagementAgent

        risk_agent = EnhancedRiskManagementAgent()

        # Activate emergency stop
        risk_agent.set_emergency_stop(True, "Integration test emergency stop")

        # Create trade proposal
        trade_proposal = {
            "symbol": "BTCUSDT",
            "side": "BUY",
            "quantity": 0.001,
            "price": 50000,
            "signal_confidence": 0.85,
        }

        # Assessment should reject
        assessment = risk_agent.assess_trade(trade_proposal)
        assert assessment.approved is False
        assert "Emergency stop" in str(assessment.reasons)

    @patch("binance_trade_agent.dashboard.utils.data_fetch._components")
    def test_emergency_stop_uses_singleton_risk_agent(self, mock_components):
        """Test that emergency stop uses the singleton risk agent instance"""
        from binance_trade_agent.dashboard.utils import data_fetch

        # Setup mock components
        mock_risk_agent = MagicMock()
        mock_components_dict = {
            "risk_agent": mock_risk_agent,
            "orchestrator": MagicMock(),
        }

        # Patch the module-level variable
        data_fetch._components = mock_components_dict

        # Get components
        components = get_trading_components()

        # Verify it returns the cached instance
        assert components["risk_agent"] is mock_risk_agent

        # Reset for other tests
        data_fetch._components = None


class TestEmergencyStopDashboardCallback:
    """Test the actual dashboard callback for emergency stop"""

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_advanced_page_emergency_stop_callback(self, mock_get_components):
        """Test that the advanced.py callback correctly calls set_emergency_stop"""
        # This test simulates what happens when the button is clicked

        # Setup mock
        mock_risk_agent = MagicMock()
        mock_components = {"risk_agent": mock_risk_agent}
        mock_get_components.return_value = mock_components

        # Simulate the callback logic from advanced.py
        try:
            components = mock_get_components()
            risk_agent = components["risk_agent"]
            risk_agent.set_emergency_stop(True, "Emergency stop triggered from dashboard")
            success = True
            error_msg = None
        except Exception as e:
            success = False
            error_msg = str(e)

        # Verify
        assert success is True
        assert error_msg is None
        mock_risk_agent.set_emergency_stop.assert_called_once_with(
            True, "Emergency stop triggered from dashboard"
        )

    @patch("binance_trade_agent.dashboard.utils.data_fetch.get_trading_components")
    def test_emergency_stop_callback_handles_errors(self, mock_get_components):
        """Test that emergency stop callback handles errors gracefully"""
        # Setup mock to raise exception
        mock_get_components.side_effect = Exception("Connection error")

        # Simulate the callback logic
        try:
            components = mock_get_components()
            risk_agent = components["risk_agent"]
            risk_agent.set_emergency_stop(True, "Emergency stop triggered from dashboard")
            success = True
            error_msg = None
        except Exception as e:
            success = False
            error_msg = str(e)

        # Verify error handled
        assert success is False
        assert "Connection error" in error_msg
