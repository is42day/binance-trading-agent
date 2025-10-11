"""
Portfolio Management Module - Tracks positions, trades, and P&L
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from decimal import Decimal
import logging


@dataclass
class Position:
    """Represents a trading position"""
    symbol: str
    side: str  # 'LONG' or 'SHORT'
    quantity: float
    average_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    timestamp: datetime
    
    @property
    def market_value(self) -> float:
        """Current market value of the position"""
        return self.quantity * self.current_price
    
    @property
    def total_pnl(self) -> float:
        """Total P&L (realized + unrealized)"""
        return self.realized_pnl + self.unrealized_pnl


@dataclass
class Trade:
    """Represents a completed trade"""
    trade_id: str
    symbol: str
    side: str  # 'BUY' or 'SELL'
    quantity: float
    price: float
    fee: float
    timestamp: datetime
    order_id: Optional[str] = None
    correlation_id: Optional[str] = None
    pnl: Optional[float] = None
    
    @property
    def total_value(self) -> float:
        """Total trade value including fees"""
        return (self.quantity * self.price) + self.fee


class PortfolioManager:
    """Manages trading portfolio with persistence"""
    
    def __init__(self, db_path: str = "portfolio.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.positions: Dict[str, Position] = {}
        self.trades: List[Trade] = []
        
        # Initialize database
        self._init_database()
        self._load_from_database()
    
    def _init_database(self):
        """Initialize SQLite database tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS positions (
                symbol TEXT PRIMARY KEY,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                average_price REAL NOT NULL,
                current_price REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        # Create trades table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                fee REAL NOT NULL,
                timestamp TEXT NOT NULL,
                order_id TEXT,
                correlation_id TEXT,
                pnl REAL
            )
        ''')
        
        # Create portfolio stats table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_stats (
                id INTEGER PRIMARY KEY,
                total_value REAL NOT NULL,
                total_pnl REAL NOT NULL,
                total_fees REAL NOT NULL,
                number_of_trades INTEGER NOT NULL,
                win_rate REAL NOT NULL,
                max_drawdown REAL NOT NULL,
                timestamp TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_from_database(self):
        """Load positions and trades from database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load positions
        cursor.execute('SELECT * FROM positions')
        for row in cursor.fetchall():
            position = Position(
                symbol=row[0],
                side=row[1],
                quantity=row[2],
                average_price=row[3],
                current_price=row[4],
                unrealized_pnl=row[5],
                realized_pnl=row[6],
                timestamp=datetime.fromisoformat(row[7])
            )
            self.positions[position.symbol] = position
        
        # Load trades
        cursor.execute('SELECT * FROM trades ORDER BY timestamp')
        for row in cursor.fetchall():
            trade = Trade(
                trade_id=row[0],
                symbol=row[1],
                side=row[2],
                quantity=row[3],
                price=row[4],
                fee=row[5],
                timestamp=datetime.fromisoformat(row[6]),
                order_id=row[7],
                correlation_id=row[8],
                pnl=row[9]
            )
            self.trades.append(trade)
        
        conn.close()
        self.logger.info(f"Loaded {len(self.positions)} positions and {len(self.trades)} trades")
    
    def add_trade(self, trade: Trade):
        """Add a new trade and update positions"""
        self.trades.append(trade)
        self._update_position_from_trade(trade)
        self._save_trade_to_database(trade)
        self._save_position_to_database(self.positions[trade.symbol])
        
        self.logger.info(f"Added trade: {trade.side} {trade.quantity} {trade.symbol} @ ${trade.price}")
    
    def _update_position_from_trade(self, trade: Trade):
        """Update position based on new trade"""
        symbol = trade.symbol
        
        if symbol not in self.positions:
            # New position
            side = 'LONG' if trade.side == 'BUY' else 'SHORT'
            self.positions[symbol] = Position(
                symbol=symbol,
                side=side,
                quantity=trade.quantity if trade.side == 'BUY' else -trade.quantity,
                average_price=trade.price,
                current_price=trade.price,
                unrealized_pnl=0.0,
                realized_pnl=-trade.fee,  # Start with fee as cost
                timestamp=trade.timestamp
            )
        else:
            # Update existing position
            position = self.positions[symbol]
            
            if trade.side == 'BUY':
                # Adding to long position or reducing short position
                if position.quantity >= 0:  # Long position
                    # Average down/up the price
                    total_value = (position.quantity * position.average_price) + (trade.quantity * trade.price)
                    total_quantity = position.quantity + trade.quantity
                    position.average_price = total_value / total_quantity if total_quantity > 0 else 0
                    position.quantity = total_quantity
                else:  # Short position
                    if abs(position.quantity) >= trade.quantity:
                        # Partially/fully covering short
                        pnl = (position.average_price - trade.price) * trade.quantity
                        position.realized_pnl += pnl - trade.fee
                        position.quantity += trade.quantity
                    else:
                        # Covering short and going long
                        cover_quantity = abs(position.quantity)
                        cover_pnl = (position.average_price - trade.price) * cover_quantity
                        position.realized_pnl += cover_pnl
                        
                        # Remaining becomes long position
                        remaining_quantity = trade.quantity - cover_quantity
                        position.quantity = remaining_quantity
                        position.average_price = trade.price
                        position.side = 'LONG'
                        position.realized_pnl -= trade.fee
            
            else:  # SELL
                # Reducing long position or adding to short position
                if position.quantity > 0:  # Long position
                    if position.quantity >= trade.quantity:
                        # Partially/fully closing long
                        pnl = (trade.price - position.average_price) * trade.quantity
                        position.realized_pnl += pnl - trade.fee
                        position.quantity -= trade.quantity
                    else:
                        # Closing long and going short
                        close_quantity = position.quantity
                        close_pnl = (trade.price - position.average_price) * close_quantity
                        position.realized_pnl += close_pnl
                        
                        # Remaining becomes short position
                        remaining_quantity = trade.quantity - close_quantity
                        position.quantity = -remaining_quantity
                        position.average_price = trade.price
                        position.side = 'SHORT'
                        position.realized_pnl -= trade.fee
                else:  # Short position
                    # Adding to short position
                    total_value = (abs(position.quantity) * position.average_price) + (trade.quantity * trade.price)
                    total_quantity = abs(position.quantity) + trade.quantity
                    position.average_price = total_value / total_quantity
                    position.quantity = -total_quantity
            
            position.timestamp = trade.timestamp
    
    def update_market_prices(self, prices: Dict[str, float]):
        """Update current market prices for all positions"""
        for symbol, position in self.positions.items():
            if symbol in prices:
                position.current_price = prices[symbol]
                
                # Calculate unrealized PnL
                if position.quantity > 0:  # Long position
                    position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity
                elif position.quantity < 0:  # Short position
                    position.unrealized_pnl = (position.average_price - position.current_price) * abs(position.quantity)
                else:
                    position.unrealized_pnl = 0.0
                
                # Save updated position
                self._save_position_to_database(position)
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """Get position for a specific symbol"""
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict[str, Position]:
        """Get all positions"""
        return self.positions.copy()
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L across all positions"""
        return sum(pos.total_pnl for pos in self.positions.values())
    
    def get_trade_history(self, symbol: Optional[str] = None, limit: Optional[int] = None) -> List[Trade]:
        """Get trade history, optionally filtered by symbol"""
        trades = self.trades
        
        if symbol:
            trades = [t for t in trades if t.symbol == symbol]
        
        # Sort by timestamp (newest first)
        trades = sorted(trades, key=lambda x: x.timestamp, reverse=True)
        
        if limit:
            trades = trades[:limit]
        
        return trades
    
    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Calculate portfolio statistics"""
        if not self.trades:
            return {
                'total_value': 0.0,
                'total_pnl': 0.0,
                'total_fees': 0.0,
                'number_of_trades': 0,
                'win_rate': 0.0,
                'max_drawdown': 0.0,
                'positions_count': len(self.positions)
            }
        
        total_fees = sum(trade.fee for trade in self.trades)
        total_pnl = self.get_total_pnl()
        total_value = self.get_portfolio_value()
        
        # Calculate win rate (trades with positive PnL)
        profitable_trades = [t for t in self.trades if t.pnl and t.pnl > 0]
        win_rate = len(profitable_trades) / len(self.trades) if self.trades else 0
        
        # Calculate max drawdown (simplified)
        running_pnl = 0
        peak_pnl = 0
        max_drawdown = 0
        
        for trade in sorted(self.trades, key=lambda x: x.timestamp):
            if trade.pnl:
                running_pnl += trade.pnl
                peak_pnl = max(peak_pnl, running_pnl)
                drawdown = peak_pnl - running_pnl
                max_drawdown = max(max_drawdown, drawdown)
        
        stats = {
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_fees': total_fees,
            'number_of_trades': len(self.trades),
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'positions_count': len(self.positions)
        }
        
        # Save stats to database
        self._save_stats_to_database(stats)
        
        return stats
    
    def _save_trade_to_database(self, trade: Trade):
        """Save trade to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO trades 
            (trade_id, symbol, side, quantity, price, fee, timestamp, order_id, correlation_id, pnl)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trade.trade_id, trade.symbol, trade.side, trade.quantity, trade.price,
            trade.fee, trade.timestamp.isoformat(), trade.order_id, trade.correlation_id, trade.pnl
        ))
        
        conn.commit()
        conn.close()
    
    def _save_position_to_database(self, position: Position):
        """Save position to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO positions 
            (symbol, side, quantity, average_price, current_price, unrealized_pnl, realized_pnl, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            position.symbol, position.side, position.quantity, position.average_price,
            position.current_price, position.unrealized_pnl, position.realized_pnl,
            position.timestamp.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def _save_stats_to_database(self, stats: Dict[str, Any]):
        """Save portfolio stats to database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO portfolio_stats 
            (total_value, total_pnl, total_fees, number_of_trades, win_rate, max_drawdown, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            stats['total_value'], stats['total_pnl'], stats['total_fees'],
            stats['number_of_trades'], stats['win_rate'], stats['max_drawdown'],
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def export_to_json(self) -> str:
        """Export portfolio data to JSON"""
        data = {
            'positions': {symbol: asdict(pos) for symbol, pos in self.positions.items()},
            'trades': [asdict(trade) for trade in self.trades],
            'stats': self.get_portfolio_stats(),
            'export_timestamp': datetime.now().isoformat()
        }
        
        # Convert datetime objects to strings for JSON serialization
        def datetime_converter(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
        
        return json.dumps(data, default=datetime_converter, indent=2)
    
    def clear_portfolio(self):
        """Clear all positions and trades (for testing/reset)"""
        self.positions.clear()
        self.trades.clear()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM positions')
        cursor.execute('DELETE FROM trades')
        cursor.execute('DELETE FROM portfolio_stats')
        conn.commit()
        conn.close()
        
        self.logger.info("Portfolio cleared")


# Demo function
def demo_portfolio_management():
    """Demo portfolio management functionality"""
    print("=== Portfolio Management Demo ===")
    
    # Initialize portfolio in writable container directory
    portfolio = PortfolioManager("/app/data/demo_portfolio.db")
    portfolio.clear_portfolio()  # Start fresh for demo
    
    # Add some demo trades
    trades = [
        Trade("trade_1", "BTCUSDT", "BUY", 0.1, 50000.0, 5.0, datetime.now(), "order_1", "corr_1"),
        Trade("trade_2", "BTCUSDT", "SELL", 0.05, 52000.0, 2.5, datetime.now(), "order_2", "corr_2"),
        Trade("trade_3", "ETHUSDT", "BUY", 1.0, 3000.0, 3.0, datetime.now(), "order_3", "corr_3"),
    ]
    
    for trade in trades:
        portfolio.add_trade(trade)
    
    # Update market prices
    portfolio.update_market_prices({
        "BTCUSDT": 51000.0,
        "ETHUSDT": 3100.0
    })
    
    # Show positions
    print("\nCurrent Positions:")
    for symbol, position in portfolio.get_all_positions().items():
        print(f"{symbol}: {position.quantity} @ ${position.average_price:.2f} "
              f"(Current: ${position.current_price:.2f}, PnL: ${position.total_pnl:.2f})")
    
    # Show stats
    stats = portfolio.get_portfolio_stats()
    print(f"\nPortfolio Stats:")
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"{key}: ${value:.2f}" if 'value' in key or 'pnl' in key else f"{key}: {value:.2%}" if 'rate' in key else f"{key}: {value:.2f}")
        else:
            print(f"{key}: {value}")
    
    # Show trade history
    print(f"\nTrade History:")
    for trade in portfolio.get_trade_history(limit=5):
        print(f"{trade.timestamp.strftime('%Y-%m-%d %H:%M:%S')}: {trade.side} {trade.quantity} {trade.symbol} @ ${trade.price:.2f}")
    
    print(f"\nPortfolio JSON export available via portfolio.export_to_json()")


if __name__ == "__main__":
    demo_portfolio_management()