#!/usr/bin/env python3
"""
Enhanced MCP Server for Binance Trading Agent
Exposes comprehensive trading functionality via Model Context Protocol
"""
import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

# Import all trading components
from binance_trade_agent.market_data_agent import MarketDataAgent
from binance_trade_agent.signal_agent import SignalAgent
from binance_trade_agent.risk_management_agent import EnhancedRiskManagementAgent
from binance_trade_agent.trade_execution_agent import TradeExecutionAgent
from binance_trade_agent.orchestrator import TradingOrchestrator
from binance_trade_agent.portfolio_manager import PortfolioManager
from binance_trade_agent.monitoring import monitoring, correlation_context


class EnhancedTradingMCPServer:
    """Enhanced MCP Server with full trading agent functionality"""
    
    def __init__(self):
        self.server = Server("binance-trading-agent")
        
        # Initialize all components
        self.market_agent = MarketDataAgent()
        self.signal_agent = SignalAgent()
        self.risk_agent = EnhancedRiskManagementAgent()
        self.execution_agent = TradeExecutionAgent()
        self.orchestrator = TradingOrchestrator()
        self.portfolio = PortfolioManager("/app/data/mcp_portfolio.db")
        
        self.logger = monitoring.get_logger('mcp_server')
        
        # Register all tools
        self._register_tools()
        
        self.logger.info("Enhanced Trading MCP Server initialized")
    
    def _register_tools(self):
        """Register all available MCP tools"""
        
        # Market Data Tools
        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            return [
                Tool(
                    name="get_market_price",
                    description="Get latest market price for a trading symbol",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTCUSDT)"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="get_order_book",
                    description="Get order book data for a trading symbol",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTCUSDT)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of order book levels (default: 20)"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="generate_trading_signal",
                    description="Generate trading signal with technical analysis",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol (e.g., BTCUSDT)"
                            },
                            "timeframe": {
                                "type": "string",
                                "description": "Timeframe for analysis (default: 1h)"
                            }
                        },
                        "required": ["symbol"]
                    }
                ),
                Tool(
                    name="validate_trade_risk",
                    description="Validate trade against risk management rules",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol"
                            },
                            "side": {
                                "type": "string",
                                "description": "Trade side (buy/sell)"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "Trade quantity"
                            },
                            "price": {
                                "type": "number",
                                "description": "Trade price"
                            }
                        },
                        "required": ["symbol", "side", "quantity", "price"]
                    }
                ),
                Tool(
                    name="execute_trading_workflow",
                    description="Execute complete trading workflow from signal to execution",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "Trade quantity"
                            },
                            "correlation_id": {
                                "type": "string",
                                "description": "Optional correlation ID for tracking"
                            }
                        },
                        "required": ["symbol", "quantity"]
                    }
                ),
                Tool(
                    name="place_buy_order",
                    description="Place a buy order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "Order quantity"
                            }
                        },
                        "required": ["symbol", "quantity"]
                    }
                ),
                Tool(
                    name="place_sell_order",
                    description="Place a sell order",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Trading symbol"
                            },
                            "quantity": {
                                "type": "number",
                                "description": "Order quantity"
                            }
                        },
                        "required": ["symbol", "quantity"]
                    }
                ),
                Tool(
                    name="get_portfolio_summary",
                    description="Get portfolio summary with positions and P&L",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_trade_history",
                    description="Get trade history",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Filter by symbol (optional)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Number of trades to return (default: 10)"
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_current_positions",
                    description="Get current open positions",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_system_status",
                    description="Get trading system health and status",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_performance_metrics",
                    description="Get performance and timing metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="get_risk_status",
                    description="Get risk management status and settings",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="set_emergency_stop",
                    description="Activate or deactivate emergency stop",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "enabled": {
                                "type": "boolean",
                                "description": "Enable or disable emergency stop"
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for emergency stop"
                            }
                        },
                        "required": ["enabled"]
                    }
                ),
                Tool(
                    name="update_market_prices",
                    description="Update portfolio with current market prices",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "List of symbols to update"
                            }
                        },
                        "required": []
                    }
                )
            ]
        
        # Tool implementations
        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """Handle MCP tool calls"""
            try:
                with correlation_context(f"mcp_{name}_{datetime.now().strftime('%H%M%S')}"):
                    self.logger.info(f"MCP tool called: {name}", context={"arguments": arguments})
                    
                    if name == "get_market_price":
                        result = await self._get_market_price(**arguments)
                    elif name == "get_order_book":
                        result = await self._get_order_book(**arguments)
                    elif name == "generate_trading_signal":
                        result = await self._generate_trading_signal(**arguments)
                    elif name == "validate_trade_risk":
                        result = await self._validate_trade_risk(**arguments)
                    elif name == "execute_trading_workflow":
                        result = await self._execute_trading_workflow(**arguments)
                    elif name == "place_buy_order":
                        result = await self._place_buy_order(**arguments)
                    elif name == "place_sell_order":
                        result = await self._place_sell_order(**arguments)
                    elif name == "get_portfolio_summary":
                        result = await self._get_portfolio_summary(**arguments)
                    elif name == "get_trade_history":
                        result = await self._get_trade_history(**arguments)
                    elif name == "get_current_positions":
                        result = await self._get_current_positions(**arguments)
                    elif name == "get_system_status":
                        result = await self._get_system_status(**arguments)
                    elif name == "get_performance_metrics":
                        result = await self._get_performance_metrics(**arguments)
                    elif name == "get_risk_status":
                        result = await self._get_risk_status(**arguments)
                    elif name == "set_emergency_stop":
                        result = await self._set_emergency_stop(**arguments)
                    elif name == "update_market_prices":
                        result = await self._update_market_prices(**arguments)
                    else:
                        raise ValueError(f"Unknown tool: {name}")
                    
                    self.logger.info(f"MCP tool completed: {name}")
                    return [TextContent(type="text", text=json.dumps(result, indent=2))]
                    
            except Exception as e:
                error_msg = f"Error in tool {name}: {str(e)}"
                self.logger.error(error_msg, context={"arguments": arguments, "error": str(e)})
                return [TextContent(type="text", text=json.dumps({"error": error_msg}, indent=2))]
    
    # Tool implementation methods
    async def _get_market_price(self, symbol: str) -> Dict[str, Any]:
        """Get market price for symbol"""
        price = self.market_agent.get_latest_price(symbol)
        return {
            "symbol": symbol,
            "price": price,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """Get order book for symbol"""
        order_book = self.market_agent.get_order_book(symbol, limit)
        return {
            "symbol": symbol,
            "order_book": order_book,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _generate_trading_signal(self, symbol: str, timeframe: str = "1h") -> Dict[str, Any]:
        """Generate trading signal"""
        signal_result = self.signal_agent.generate_signal(symbol)
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "signal": signal_result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _validate_trade_risk(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """Validate trade risk"""
        portfolio_value = self.portfolio.get_portfolio_value() or 100000.0
        
        result = self.risk_agent.validate_trade(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            portfolio_value=portfolio_value
        )
        
        return {
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "risk_assessment": result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _execute_trading_workflow(self, symbol: str, quantity: float, correlation_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute complete trading workflow"""
        decision = await self.orchestrator.execute_trading_workflow(symbol, quantity, correlation_id)
        
        return {
            "symbol": symbol,
            "quantity": quantity,
            "decision": {
                "signal_type": decision.signal_type,
                "confidence": decision.confidence,
                "price": decision.price,
                "risk_approved": decision.risk_approved,
                "executed": decision.executed,
                "order_id": decision.order_id,
                "execution_price": decision.execution_price,
                "correlation_id": decision.correlation_id
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _place_buy_order(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Place buy order"""
        result = self.execution_agent.place_buy_order(symbol, quantity)
        return {
            "symbol": symbol,
            "quantity": quantity,
            "side": "BUY",
            "order_result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _place_sell_order(self, symbol: str, quantity: float) -> Dict[str, Any]:
        """Place sell order"""
        result = self.execution_agent.place_sell_order(symbol, quantity)
        return {
            "symbol": symbol,
            "quantity": quantity,
            "side": "SELL",
            "order_result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary"""
        stats = self.portfolio.get_portfolio_stats()
        return {
            "portfolio_stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_trade_history(self, symbol: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
        """Get trade history"""
        trades = self.portfolio.get_trade_history(symbol=symbol, limit=limit)
        return {
            "symbol_filter": symbol,
            "limit": limit,
            "trades": [
                {
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "side": trade.side,
                    "quantity": trade.quantity,
                    "price": trade.price,
                    "fee": trade.fee,
                    "timestamp": trade.timestamp.isoformat(),
                    "order_id": trade.order_id,
                    "correlation_id": trade.correlation_id
                }
                for trade in trades
            ],
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_current_positions(self) -> Dict[str, Any]:
        """Get current positions"""
        positions = self.portfolio.get_all_positions()
        return {
            "positions": {
                symbol: {
                    "symbol": pos.symbol,
                    "side": pos.side,
                    "quantity": pos.quantity,
                    "average_price": pos.average_price,
                    "current_price": pos.current_price,
                    "unrealized_pnl": pos.unrealized_pnl,
                    "realized_pnl": pos.realized_pnl,
                    "market_value": pos.market_value,
                    "total_pnl": pos.total_pnl
                }
                for symbol, pos in positions.items()
                if pos.quantity != 0  # Only show non-zero positions
            },
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        health = monitoring.get_health_status()
        return {
            "system_status": health,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        metrics = monitoring.get_performance_metrics()
        return {
            "performance_metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _get_risk_status(self) -> Dict[str, Any]:
        """Get risk status"""
        risk_status = self.risk_agent.get_risk_status()
        return {
            "risk_status": risk_status,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _set_emergency_stop(self, enabled: bool, reason: str = "") -> Dict[str, Any]:
        """Set emergency stop"""
        self.risk_agent.set_emergency_stop(enabled, reason)
        return {
            "emergency_stop": enabled,
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
    
    async def _update_market_prices(self, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update market prices for portfolio"""
        if not symbols:
            # Get symbols from current positions
            positions = self.portfolio.get_all_positions()
            symbols = list(positions.keys())
        
        if not symbols:
            return {
                "message": "No symbols to update",
                "timestamp": datetime.now().isoformat()
            }
        
        # Get current prices
        prices = {}
        for symbol in symbols:
            try:
                prices[symbol] = self.market_agent.get_latest_price(symbol)
            except Exception as e:
                self.logger.warning(f"Failed to get price for {symbol}: {str(e)}")
        
        # Update portfolio
        if prices:
            self.portfolio.update_market_prices(prices)
        
        return {
            "updated_symbols": list(prices.keys()),
            "prices": prices,
            "timestamp": datetime.now().isoformat()
        }


# Module-level server instance for imports
server = EnhancedTradingMCPServer()


async def main():
    """Main function to run the MCP server"""
    # Run the server
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await server.server.run(
            read_stream,
            write_stream,
            server.server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())