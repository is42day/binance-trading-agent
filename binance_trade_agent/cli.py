#!/usr/bin/env python3
"""
Command Line Interface for Binance Trading Agent
Provides interactive commands for testing and controlling the trading system
"""
import asyncio
import cmd
import json
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List
import argparse
from tabulate import tabulate

# Import trading agent components
from .orchestrator import TradingOrchestrator
from .portfolio_manager import PortfolioManager, Trade
from .risk_management_agent import EnhancedRiskManagementAgent
from .monitoring import monitoring, correlation_context
from .market_data_agent import MarketDataAgent
from .signal_agent import SignalAgent
from .trade_execution_agent import TradeExecutionAgent


class TradingCLI(cmd.Cmd):
    """Interactive CLI for trading agent"""
    
    intro = '''
╔══════════════════════════════════════════════════════════════════════════════╗
║                     Binance Trading Agent CLI v1.0                          ║
║                                                                              ║
║ Available commands:                                                          ║
║   help           - Show help for commands                                    ║
║   buy <symbol> <quantity>    - Place buy order                              ║
║   sell <symbol> <quantity>   - Place sell order                             ║
║   status         - Show system status                                       ║
║   portfolio      - Show portfolio summary                                   ║
║   positions      - Show current positions                                   ║
║   trades         - Show trade history                                       ║
║   signals <symbol>   - Get trading signals                                  ║
║   risk <symbol> <side> <qty> <price> - Test risk management                 ║
║   market <symbol>    - Get market data                                      ║
║   orders         - Show active orders                                       ║
║   cancel <order_id>  - Cancel order                                         ║
║   metrics        - Show performance metrics                                 ║
║   logs           - Show recent logs                                         ║
║   config         - Show configuration                                       ║
║   emergency      - Emergency stop all trading                              ║
║   webui          - Launch web UI dashboard                                 ║
║   quit           - Exit the CLI                                             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Type 'help <command>' for detailed help on specific commands.
'''
    
    prompt = '(trading) '
    
    def __init__(self):
        super().__init__()
        
        # Initialize components
        self.orchestrator = TradingOrchestrator()
        self.portfolio = PortfolioManager("trading_cli.db")
        self.risk_agent = EnhancedRiskManagementAgent()
        self.market_agent = MarketDataAgent()
        self.signal_agent = SignalAgent()
        self.execution_agent = TradeExecutionAgent()
        
        self.logger = monitoring.get_logger('trading_cli')
        
        # CLI state
        self.active_orders: List[Dict[str, Any]] = []
        self.emergency_stop = False
        
        print(self.intro)
        self.logger.info("Trading CLI initialized")
    
    def do_buy(self, line):
        """
        Place a buy order
        Usage: buy <symbol> <quantity>
        Example: buy BTCUSDT 0.001
        """
        try:
            parts = line.split()
            if len(parts) != 2:
                print("Error: Invalid syntax. Use: buy <symbol> <quantity>")
                return
            
            symbol = parts[0].upper()
            quantity = float(parts[1])
            
            with correlation_context(f"cli_buy_{datetime.now().strftime('%H%M%S')}"):
                asyncio.run(self._execute_buy_order(symbol, quantity))
                
        except ValueError:
            print("Error: Invalid quantity. Must be a number.")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    def do_sell(self, line):
        """
        Place a sell order
        Usage: sell <symbol> <quantity>
        Example: sell BTCUSDT 0.001
        """
        try:
            parts = line.split()
            if len(parts) != 2:
                print("Error: Invalid syntax. Use: sell <symbol> <quantity>")
                return
            
            symbol = parts[0].upper()
            quantity = float(parts[1])
            
            with correlation_context(f"cli_sell_{datetime.now().strftime('%H%M%S')}"):
                asyncio.run(self._execute_sell_order(symbol, quantity))
                
        except ValueError:
            print("Error: Invalid quantity. Must be a number.")
        except Exception as e:
            print(f"Error: {str(e)}")
    
    async def _execute_buy_order(self, symbol: str, quantity: float):
        """Execute buy order through orchestrator"""
        try:
            print(f"Placing BUY order: {quantity} {symbol}")
            decision = await self.orchestrator.execute_trading_workflow(symbol, quantity)
            
            if decision.executed:
                print(f"✅ Order executed successfully!")
                print(f"   Order ID: {decision.order_id}")
                print(f"   Price: ${decision.execution_price:,.2f}")
                print(f"   Signal: {decision.signal_type} (confidence: {decision.confidence:.1%})")
                
                # Add to portfolio
                trade = Trade(
                    trade_id=decision.order_id or f"cli_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    symbol=symbol,
                    side="BUY",
                    quantity=quantity,
                    price=decision.execution_price or decision.price,
                    fee=quantity * (decision.execution_price or decision.price) * 0.001,  # Assume 0.1% fee
                    timestamp=datetime.now(),
                    correlation_id=decision.correlation_id
                )
                self.portfolio.add_trade(trade)
                
            else:
                print(f"❌ Order rejected")
                print(f"   Reason: Risk not approved")
                print(f"   Signal: {decision.signal_type} (confidence: {decision.confidence:.1%})")
                
        except Exception as e:
            print(f"❌ Order failed: {str(e)}")
    
    async def _execute_sell_order(self, symbol: str, quantity: float):
        """Execute sell order through orchestrator"""
        try:
            print(f"Placing SELL order: {quantity} {symbol}")
            
            # For sell orders, we need to override the signal
            # This is a manual sell, so we'll validate risk directly
            price = self.market_agent.get_latest_price(symbol)
            
            risk_result = self.risk_agent.validate_trade(
                symbol=symbol,
                side='sell',
                quantity=quantity,
                price=price,
                portfolio_value=self.portfolio.get_portfolio_value() or 100000.0
            )
            
            if risk_result['approved']:
                result = self.execution_agent.place_sell_order(symbol, quantity)
                
                print(f"✅ SELL order executed successfully!")
                print(f"   Order ID: {result.get('order_id', 'N/A')}")
                print(f"   Price: ${price:,.2f}")
                
                # Add to portfolio
                trade = Trade(
                    trade_id=result.get('order_id', f"cli_sell_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                    symbol=symbol,
                    side="SELL",
                    quantity=quantity,
                    price=price,
                    fee=quantity * price * 0.001,  # Assume 0.1% fee
                    timestamp=datetime.now()
                )
                self.portfolio.add_trade(trade)
                
            else:
                print(f"❌ SELL order rejected")
                print(f"   Reason: {risk_result['reason']}")
                
        except Exception as e:
            print(f"❌ SELL order failed: {str(e)}")
    
    def do_status(self, line):
        """
        Show system status
        Usage: status
        """
        try:
            print("\n" + "="*60)
            print("SYSTEM STATUS")
            print("="*60)
            
            # Health status
            health = monitoring.get_health_status()
            status_emoji = "🟢" if health['status'] == 'healthy' else "🟡"
            print(f"System Health: {status_emoji} {health['status'].upper()}")
            print(f"Uptime: {health['uptime_seconds']:.0f} seconds")
            print(f"Trade Error Rate: {health['trade_error_rate']:.1%}")
            print(f"API Error Rate: {health['api_error_rate']:.1%}")
            
            # Portfolio summary
            portfolio_value = health.get('portfolio_value', 0) or 0
            open_positions = health.get('open_positions', 0)
            total_pnl = self.portfolio.get_total_pnl()
            
            print(f"\nPortfolio Value: ${portfolio_value:,.2f}")
            print(f"Total P&L: ${total_pnl:,.2f}")
            print(f"Open Positions: {open_positions}")
            print(f"Total Trades: {int(health['total_trades'])}")
            
            # Risk status
            risk_status = self.risk_agent.get_risk_status()
            emergency_emoji = "🔴" if risk_status['emergency_stop'] else "🟢"
            print(f"Emergency Stop: {emergency_emoji} {'ACTIVE' if risk_status['emergency_stop'] else 'INACTIVE'}")
            print(f"Consecutive Losses: {risk_status['consecutive_losses']}")
            print(f"Daily Trades: {risk_status['daily_trades']}")
            
            print("="*60)
            
        except Exception as e:
            print(f"Error getting status: {str(e)}")
    
    def do_portfolio(self, line):
        """
        Show portfolio summary
        Usage: portfolio
        """
        try:
            print("\n" + "="*60)
            print("PORTFOLIO SUMMARY")
            print("="*60)
            
            stats = self.portfolio.get_portfolio_stats()
            
            print(f"Total Value: ${stats['total_value']:,.2f}")
            print(f"Total P&L: ${stats['total_pnl']:,.2f}")
            print(f"Total Fees: ${stats['total_fees']:,.2f}")
            print(f"Number of Trades: {stats['number_of_trades']}")
            print(f"Win Rate: {stats['win_rate']:.1%}")
            print(f"Max Drawdown: ${stats['max_drawdown']:,.2f}")
            print(f"Active Positions: {stats['positions_count']}")
            
            print("="*60)
            
        except Exception as e:
            print(f"Error getting portfolio: {str(e)}")
    
    def do_positions(self, line):
        """
        Show current positions
        Usage: positions
        """
        try:
            positions = self.portfolio.get_all_positions()
            
            if not positions:
                print("No open positions.")
                return
            
            print("\n" + "="*80)
            print("CURRENT POSITIONS")
            print("="*80)
            
            headers = ["Symbol", "Side", "Quantity", "Avg Price", "Current Price", "Unrealized P&L", "Market Value"]
            rows = []
            
            for symbol, position in positions.items():
                if position.quantity != 0:  # Only show non-zero positions
                    rows.append([
                        symbol,
                        position.side,
                        f"{position.quantity:.6f}",
                        f"${position.average_price:,.2f}",
                        f"${position.current_price:,.2f}",
                        f"${position.unrealized_pnl:,.2f}",
                        f"${position.market_value:,.2f}"
                    ])
            
            if rows:
                print(tabulate(rows, headers=headers, tablefmt="grid"))
            else:
                print("No active positions.")
            
            print("="*80)
            
        except Exception as e:
            print(f"Error getting positions: {str(e)}")
    
    def do_trades(self, line):
        """
        Show trade history
        Usage: trades [limit]
        Example: trades 10
        """
        try:
            limit = 10  # Default
            if line.strip():
                limit = int(line.strip())
            
            trades = self.portfolio.get_trade_history(limit=limit)
            
            if not trades:
                print("No trades found.")
                return
            
            print(f"\n" + "="*100)
            print(f"TRADE HISTORY (Last {len(trades)} trades)")
            print("="*100)
            
            headers = ["Time", "Symbol", "Side", "Quantity", "Price", "Fee", "Order ID"]
            rows = []
            
            for trade in trades:
                rows.append([
                    trade.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    trade.symbol,
                    trade.side,
                    f"{trade.quantity:.6f}",
                    f"${trade.price:,.2f}",
                    f"${trade.fee:,.2f}",
                    trade.order_id or "N/A"
                ])
            
            print(tabulate(rows, headers=headers, tablefmt="grid"))
            print("="*100)
            
        except ValueError:
            print("Error: Invalid limit. Must be a number.")
        except Exception as e:
            print(f"Error getting trades: {str(e)}")
    
    def do_signals(self, line):
        """
        Get trading signals for a symbol
        Usage: signals <symbol>
        Example: signals BTCUSDT
        """
        try:
            if not line.strip():
                print("Error: Please specify a symbol. Use: signals <symbol>")
                return
            
            symbol = line.strip().upper()
            
            print(f"Generating signals for {symbol}...")
            
            # Get market data
            price = self.market_agent.get_latest_price(symbol)
            
            # Generate signal
            signal_result = self.signal_agent.generate_signal(symbol)
            
            print(f"\n" + "="*50)
            print(f"TRADING SIGNALS - {symbol}")
            print("="*50)
            print(f"Current Price: ${price:,.2f}")
            print(f"Signal: {signal_result['signal']}")
            print(f"Confidence: {signal_result['confidence']:.1%}")
            print(f"Indicator: {signal_result.get('indicator', 'N/A')}")
            print(f"Indicator Value: {signal_result.get('indicator_value', 'N/A')}")
            print("="*50)
            
        except Exception as e:
            print(f"Error getting signals: {str(e)}")
    
    def do_risk(self, line):
        """
        Test risk management for a trade
        Usage: risk <symbol> <side> <quantity> <price>
        Example: risk BTCUSDT buy 0.001 50000
        """
        try:
            parts = line.split()
            if len(parts) != 4:
                print("Error: Invalid syntax. Use: risk <symbol> <side> <quantity> <price>")
                return
            
            symbol = parts[0].upper()
            side = parts[1].lower()
            quantity = float(parts[2])
            price = float(parts[3])
            
            portfolio_value = self.portfolio.get_portfolio_value() or 100000.0
            
            result = self.risk_agent.validate_trade(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                portfolio_value=portfolio_value
            )
            
            print(f"\n" + "="*60)
            print(f"RISK ASSESSMENT - {side.upper()} {quantity} {symbol} @ ${price:,.2f}")
            print("="*60)
            
            status_emoji = "✅" if result['approved'] else "❌"
            print(f"Status: {status_emoji} {'APPROVED' if result['approved'] else 'REJECTED'}")
            print(f"Risk Level: {result['risk_level'].upper()}")
            print(f"Reason: {result['reason']}")
            
            if result['warnings']:
                print(f"Warnings:")
                for warning in result['warnings']:
                    print(f"  ⚠️  {warning}")
            
            if result['recommended_quantity']:
                print(f"Recommended Quantity: {result['recommended_quantity']:.6f}")
            
            if result['stop_loss_price']:
                print(f"Stop Loss: ${result['stop_loss_price']:,.2f}")
            
            if result['take_profit_price']:
                print(f"Take Profit: ${result['take_profit_price']:,.2f}")
            
            print("="*60)
            
        except ValueError:
            print("Error: Invalid number format.")
        except Exception as e:
            print(f"Error in risk assessment: {str(e)}")
    
    def do_market(self, line):
        """
        Get market data for a symbol
        Usage: market <symbol>
        Example: market BTCUSDT
        """
        try:
            if not line.strip():
                print("Error: Please specify a symbol. Use: market <symbol>")
                return
            
            symbol = line.strip().upper()
            
            print(f"Fetching market data for {symbol}...")
            
            # Get current price
            price = self.market_agent.get_latest_price(symbol)
            
            # Get order book (if available)
            try:
                order_book = self.market_agent.get_order_book(symbol)
                best_bid = order_book['bids'][0][0] if order_book['bids'] else 0
                best_ask = order_book['asks'][0][0] if order_book['asks'] else 0
                spread = best_ask - best_bid if best_ask and best_bid else 0
            except:
                best_bid = best_ask = spread = 0
            
            print(f"\n" + "="*40)
            print(f"MARKET DATA - {symbol}")
            print("="*40)
            print(f"Current Price: ${price:,.2f}")
            if best_bid and best_ask:
                print(f"Best Bid: ${best_bid:,.2f}")
                print(f"Best Ask: ${best_ask:,.2f}")
                print(f"Spread: ${spread:,.2f}")
            print("="*40)
            
        except Exception as e:
            print(f"Error getting market data: {str(e)}")
    
    def do_orders(self, line):
        """
        Show active orders
        Usage: orders
        """
        print("Active orders feature not implemented yet.")
        print("Note: This would show real orders from Binance API in production.")
    
    def do_cancel(self, line):
        """
        Cancel an order
        Usage: cancel <order_id>
        Example: cancel 12345
        """
        if not line.strip():
            print("Error: Please specify an order ID. Use: cancel <order_id>")
            return
        
        order_id = line.strip()
        print(f"Cancel order feature not implemented yet.")
        print(f"Note: Would cancel order {order_id} via Binance API in production.")
    
    def do_metrics(self, line):
        """
        Show performance metrics
        Usage: metrics
        """
        try:
            print("\n" + "="*60)
            print("PERFORMANCE METRICS")
            print("="*60)
            
            perf = monitoring.get_performance_metrics()
            
            for category, stats in perf.items():
                if stats:
                    print(f"\n{category.replace('_', ' ').title()}:")
                    for key, value in stats.items():
                        if isinstance(value, float):
                            if 'ms' in key:
                                print(f"  {key}: {value:.1f}ms")
                            else:
                                print(f"  {key}: {value:.3f}")
                        else:
                            print(f"  {key}: {value}")
            
            print("="*60)
            
        except Exception as e:
            print(f"Error getting metrics: {str(e)}")
    
    def do_logs(self, line):
        """
        Show recent logs
        Usage: logs [limit] [level]
        Example: logs 20 ERROR
        """
        try:
            parts = line.split()
            limit = 10
            level = None
            
            if len(parts) >= 1:
                try:
                    limit = int(parts[0])
                except ValueError:
                    level = parts[0].upper()
            
            if len(parts) >= 2:
                level = parts[1].upper()
            
            logger = monitoring.get_logger('trading_cli')
            logs = logger.get_recent_logs(limit=limit, level=level)
            
            if not logs:
                print("No logs found.")
                return
            
            print(f"\n" + "="*100)
            print(f"RECENT LOGS ({len(logs)} entries)")
            if level:
                print(f"Filtered by level: {level}")
            print("="*100)
            
            for log in logs:
                timestamp = log['timestamp'][:19]  # Remove microseconds
                level_emoji = {"INFO": "ℹ️", "WARNING": "⚠️", "ERROR": "❌", "CRITICAL": "🔥", "DEBUG": "🐛"}.get(log['level'], "📝")
                print(f"{timestamp} {level_emoji} [{log['correlation_id'][:8]}] {log['message']}")
            
            print("="*100)
            
        except Exception as e:
            print(f"Error getting logs: {str(e)}")
    
    def do_config(self, line):
        """
        Show current configuration
        Usage: config
        """
        try:
            print("\n" + "="*60)
            print("CONFIGURATION")
            print("="*60)
            
            risk_status = self.risk_agent.get_risk_status()
            
            print("Risk Management:")
            print(f"  Emergency Stop: {'ACTIVE' if risk_status['emergency_stop'] else 'INACTIVE'}")
            print(f"  Max Position per Symbol: {self.risk_agent.config['max_position_per_symbol']:.1%}")
            print(f"  Max Single Trade: {self.risk_agent.config['max_single_trade_size']:.1%}")
            print(f"  Default Stop Loss: {self.risk_agent.config['default_stop_loss_pct']:.1%}")
            print(f"  Default Take Profit: {self.risk_agent.config['default_take_profit_pct']:.1%}")
            print(f"  Max Daily Trades: {self.risk_agent.config['max_trades_per_day']}")
            
            print("="*60)
            
        except Exception as e:
            print(f"Error getting config: {str(e)}")
    
    def do_emergency(self, line):
        """
        Emergency stop all trading
        Usage: emergency [on|off]
        Example: emergency on
        """
        try:
            if not line.strip():
                # Show current status
                status = self.risk_agent.get_risk_status()
                current = "ACTIVE" if status['emergency_stop'] else "INACTIVE"
                print(f"Emergency stop is currently: {current}")
                print("Use 'emergency on' or 'emergency off' to change.")
                return
            
            action = line.strip().lower()
            
            if action == 'on':
                self.risk_agent.set_emergency_stop(True, "CLI command")
                print("🔴 EMERGENCY STOP ACTIVATED")
                print("All trading is now disabled.")
                
            elif action == 'off':
                confirm = input("Are you sure you want to deactivate emergency stop? (yes/no): ")
                if confirm.lower() == 'yes':
                    self.risk_agent.set_emergency_stop(False, "CLI command")
                    print("🟢 Emergency stop deactivated")
                    print("Trading is now enabled.")
                else:
                    print("Emergency stop remains active.")
                    
            else:
                print("Error: Use 'emergency on' or 'emergency off'")
                
        except Exception as e:
            print(f"Error setting emergency stop: {str(e)}")
    
    def do_webui(self, line):
        """
        Launch web UI dashboard
        Usage: webui
        """
        try:
            import subprocess
            import sys
            
            print("🚀 Launching Streamlit web UI...")
            print("Access the dashboard at: http://localhost:8501")
            print("Press Ctrl+C in this terminal to stop the web UI")
            print("-" * 50)
            
            # Launch streamlit
            subprocess.run([
                sys.executable, "-m", "streamlit", "run", 
                "binance_trade_agent/web_ui.py"
            ])
            
        except KeyboardInterrupt:
            print("\n🛑 Web UI stopped")
        except Exception as e:
            print(f"Error launching web UI: {str(e)}")
            print("Make sure Streamlit is installed: pip install streamlit")
    
    def do_quit(self, line):
        """
        Exit the CLI
        Usage: quit
        """
        print("Goodbye! 👋")
        return True
    
    def do_exit(self, line):
        """Alias for quit"""
        return self.do_quit(line)
    
    def emptyline(self):
        """Override to do nothing on empty line"""
        pass
    
    def default(self, line):
        """Handle unknown commands"""
        print(f"Unknown command: {line}")
        print("Type 'help' for available commands.")


def run_cli():
    """Run the CLI interface"""
    try:
        cli = TradingCLI()
        cli.cmdloop()
    except KeyboardInterrupt:
        print("\nExiting...")
    except Exception as e:
        print(f"CLI Error: {str(e)}")


def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(description='Binance Trading Agent CLI')
    parser.add_argument('--command', '-c', help='Execute a single command and exit')
    parser.add_argument('--batch', '-b', help='Execute commands from a file')
    
    args = parser.parse_args()
    
    if args.command:
        # Execute single command
        cli = TradingCLI()
        cli.onecmd(args.command)
    elif args.batch:
        # Execute batch commands
        cli = TradingCLI()
        try:
            with open(args.batch, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        print(f"Executing: {line}")
                        cli.onecmd(line)
        except FileNotFoundError:
            print(f"Error: Batch file '{args.batch}' not found")
    else:
        # Interactive mode
        run_cli()


if __name__ == "__main__":
    main()