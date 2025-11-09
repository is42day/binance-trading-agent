"""
Portfolio Management Module - Tracks positions, trades, and P&L using SQLAlchemy ORM
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from decimal import Decimal

from sqlalchemy import create_engine, Column, String, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, Session as SQLAlchemySession

# Initialize SQLAlchemy
Base = declarative_base()

# ============================================================================
# SQLAlchemy ORM Models (Top-Level Definition)
# ============================================================================

class PositionORM(Base):
    """ORM model for trading positions"""
    __tablename__ = 'positions'
    
    symbol = Column(String, primary_key=True)
    side = Column(String, nullable=False)  # LONG or SHORT
    quantity = Column(Float, nullable=False)
    average_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, nullable=False)
    realized_pnl = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        return {
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'average_price': self.average_price,
            'current_price': self.current_price,
            'unrealized_pnl': self.unrealized_pnl,
            'realized_pnl': self.realized_pnl,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'market_value': self.quantity * self.current_price,
            'total_pnl': self.realized_pnl + self.unrealized_pnl
        }


class TradeORM(Base):
    """ORM model for executed trades"""
    __tablename__ = 'trades'
    
    trade_id = Column(String, primary_key=True)
    symbol = Column(String, nullable=False)
    side = Column(String, nullable=False)  # BUY or SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    fee = Column(Float, nullable=False)
    timestamp = Column(DateTime, nullable=False)
    order_id = Column(String, nullable=True)
    correlation_id = Column(String, nullable=True)
    pnl = Column(Float, nullable=True)

    def to_dict(self) -> Dict[str, Any]:
        """Convert ORM object to dictionary"""
        return {
            'trade_id': self.trade_id,
            'symbol': self.symbol,
            'side': self.side,
            'quantity': self.quantity,
            'price': self.price,
            'fee': self.fee,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'order_id': self.order_id,
            'correlation_id': self.correlation_id,
            'pnl': self.pnl,
            'total_value': (self.quantity * self.price) + self.fee
        }


# ============================================================================
# Portfolio Manager - SQLAlchemy-Based Implementation
# ============================================================================

class PortfolioManager:
    """Manages portfolio positions, trades, and P&L using SQLAlchemy ORM"""
    
    def __init__(self, db_path: str = "/app/data/portfolio.db"):
        """Initialize portfolio manager with SQLAlchemy session"""
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_session(self) -> SQLAlchemySession:
        """Get a new database session"""
        return self.SessionLocal()
    
    def add_trade(self, trade_id: str, symbol: str, side: str, quantity: float, 
                  price: float, fee: float, order_id: Optional[str] = None,
                  correlation_id: Optional[str] = None, pnl: Optional[float] = None) -> TradeORM:
        """Add a new trade to the portfolio"""
        session = self.get_session()
        try:
            trade = TradeORM(
                trade_id=trade_id,
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                fee=fee,
                timestamp=datetime.now(),
                order_id=order_id,
                correlation_id=correlation_id,
                pnl=pnl
            )
            session.add(trade)
            session.commit()
            self.logger.info(f"Added trade: {side} {quantity} {symbol} @ ${price:.2f}")
            
            # Update position based on trade (pass the TradeORM object, not dict)
            self._update_position_from_trade(session, trade)
            
            return trade
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error adding trade: {str(e)}")
            raise
        finally:
            session.close()
    
    def _update_position_from_trade(self, session: SQLAlchemySession, trade):
        """Update position based on new trade"""
        try:
            # Handle both TradeORM objects and dictionaries
            if isinstance(trade, dict):
                symbol = trade.get('symbol')
                side = trade.get('side')
                quantity = trade.get('quantity')
                price = trade.get('price')
                fee = trade.get('fee', 0.001)  # Default fee
            else:
                # Assume it's a TradeORM object
                symbol = trade.symbol
                side = trade.side
                quantity = trade.quantity
                price = trade.price
                fee = getattr(trade, 'fee', 0.001)  # Default fee
            
            # Validate required fields
            if not symbol or not side or quantity is None or price is None:
                error_msg = f"Invalid trade data: symbol={symbol}, side={side}, quantity={quantity}, price={price}"
                self.logger.error(error_msg)
                raise ValueError(error_msg)
            
            position = session.query(PositionORM).filter_by(symbol=symbol).first()
            
            if position is None:
                # Create new position
                side_str = 'LONG' if side == 'BUY' else 'SHORT'
                quantity_val = quantity if side == 'BUY' else -quantity
                
                position = PositionORM(
                    symbol=symbol,
                    side=side_str,
                    quantity=quantity_val,
                    average_price=price,
                    current_price=price,
                    unrealized_pnl=0.0,
                    realized_pnl=-fee,
                    timestamp=datetime.now()
                )
                session.add(position)
            else:
                # Update existing position
                if side == 'BUY':
                    if position.quantity >= 0:
                        # Adding to long position
                        total_value = (position.quantity * position.average_price) + (quantity * price)
                        total_quantity = position.quantity + quantity
                        position.average_price = total_value / total_quantity if total_quantity > 0 else 0
                        position.quantity = total_quantity
                    else:
                        # Reducing short position or going long
                        if abs(position.quantity) >= quantity:
                            pnl = (position.average_price - price) * quantity
                            position.realized_pnl += pnl - fee
                            position.quantity += quantity
                        else:
                            cover_quantity = abs(position.quantity)
                            cover_pnl = (position.average_price - price) * cover_quantity
                            position.realized_pnl += cover_pnl
                            
                            remaining_quantity = quantity - cover_quantity
                            position.quantity = remaining_quantity
                            position.average_price = price
                            position.side = 'LONG'
                            position.realized_pnl -= fee
                
                else:  # SELL
                    if position.quantity > 0:
                        # Reducing long position
                        if position.quantity >= quantity:
                            pnl = (price - position.average_price) * quantity
                            position.realized_pnl += pnl - fee
                            position.quantity -= quantity
                        else:
                            close_quantity = position.quantity
                            close_pnl = (price - position.average_price) * close_quantity
                            position.realized_pnl += close_pnl
                            
                            remaining_quantity = quantity - close_quantity
                            position.quantity = -remaining_quantity
                            position.average_price = price
                            position.side = 'SHORT'
                            position.realized_pnl -= fee
                    else:
                        # Adding to short position
                        total_value = (abs(position.quantity) * position.average_price) + (quantity * price)
                        total_quantity = abs(position.quantity) + quantity
                        position.average_price = total_value / total_quantity
                        position.quantity = -total_quantity
                
                position.timestamp = datetime.now()
            
            session.commit()
            self.logger.info(f"Position updated for {symbol}")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating position: {str(e)}")
            raise
    
    def update_market_prices(self, prices: Dict[str, float]):
        """Update current market prices for all positions"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            
            for position in positions:
                if position.symbol in prices:
                    position.current_price = prices[position.symbol]
                    
                    # Calculate unrealized PnL
                    if position.quantity > 0:
                        position.unrealized_pnl = (position.current_price - position.average_price) * position.quantity
                    elif position.quantity < 0:
                        position.unrealized_pnl = (position.average_price - position.current_price) * abs(position.quantity)
                    else:
                        position.unrealized_pnl = 0.0
            
            session.commit()
            self.logger.info(f"Updated prices for {len(prices)} symbols")
        except Exception as e:
            session.rollback()
            self.logger.error(f"Error updating market prices: {str(e)}")
            raise
        finally:
            session.close()
    
    def get_position(self, symbol: str) -> Optional[PositionORM]:
        """Get position for a specific symbol"""
        session = self.get_session()
        try:
            position = session.query(PositionORM).filter_by(symbol=symbol).first()
            return position
        finally:
            session.close()
    
    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get all positions as dictionaries"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            return [pos.to_dict() for pos in positions]
        finally:
            session.close()
    
    def get_portfolio_value(self) -> float:
        """Calculate total portfolio value"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            return sum(pos.quantity * pos.current_price for pos in positions)
        finally:
            session.close()
    
    def get_total_pnl(self) -> float:
        """Calculate total P&L across all positions"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            return sum((pos.realized_pnl + pos.unrealized_pnl) for pos in positions)
        finally:
            session.close()
    
    def get_trade_history(self, symbol: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get trade history, optionally filtered by symbol"""
        session = self.get_session()
        try:
            query = session.query(TradeORM)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            
            trades = query.order_by(TradeORM.timestamp.desc()).all()
            
            if limit:
                trades = trades[:limit]
            
            return [trade.to_dict() for trade in trades]
        finally:
            session.close()
    
    def get_portfolio_stats(self) -> Dict[str, Any]:
        """Calculate portfolio statistics"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            trades = session.query(TradeORM).all()
            
            total_value = sum(pos.quantity * pos.current_price for pos in positions)
            total_pnl = sum((pos.realized_pnl + pos.unrealized_pnl) for pos in positions)
            total_fees = sum(trade.fee for trade in trades)
            
            # Calculate win rate
            profitable_trades = [t for t in trades if t.pnl and t.pnl > 0]
            win_rate = len(profitable_trades) / len(trades) if trades else 0.0
            
            # Calculate max drawdown
            running_pnl = 0.0
            peak_pnl = 0.0
            max_drawdown = 0.0
            
            for trade in sorted(trades, key=lambda x: x.timestamp):
                if trade.pnl:
                    running_pnl += trade.pnl
                    peak_pnl = max(peak_pnl, running_pnl)
                    drawdown = peak_pnl - running_pnl
                    max_drawdown = max(max_drawdown, drawdown)
            
            return {
                'total_value': total_value,
                'total_pnl': total_pnl,
                'total_fees': total_fees,
                'number_of_trades': len(trades),
                'win_rate': win_rate,
                'max_drawdown': max_drawdown,
                'positions_count': len(positions)
            }
        finally:
            session.close()
    
    def export_to_json(self) -> str:
        """Export portfolio data to JSON"""
        session = self.get_session()
        try:
            positions = session.query(PositionORM).all()
            trades = session.query(TradeORM).all()
            
            data = {
                'positions': [pos.to_dict() for pos in positions],
                'trades': [trade.to_dict() for trade in trades],
                'stats': self.get_portfolio_stats(),
                'export_timestamp': datetime.now().isoformat()
            }
            
            return json.dumps(data, indent=2)
        finally:
            session.close()
    
    def clear_portfolio(self):
        """Clear all positions and trades (for testing/reset)"""
        session = self.get_session()
        try:
            session.query(PositionORM).delete()
            session.query(TradeORM).delete()
            session.commit()
            self.logger.info("Portfolio cleared")
        finally:
            session.close()


# ============================================================================
# Demo Function
# ============================================================================

def demo_portfolio_management():
    """Demo portfolio management functionality"""
    print("=== Portfolio Management Demo ===\n")
    
    # Initialize portfolio
    portfolio = PortfolioManager("/app/data/demo_portfolio.db")
    portfolio.clear_portfolio()
    
    # Add demo trades
    trades_data = [
        ("trade_1", "BTCUSDT", "BUY", 0.1, 50000.0, 5.0, "order_1", "corr_1"),
        ("trade_2", "BTCUSDT", "SELL", 0.05, 52000.0, 2.5, "order_2", "corr_2"),
        ("trade_3", "ETHUSDT", "BUY", 1.0, 3000.0, 3.0, "order_3", "corr_3"),
    ]
    
    for trade_id, symbol, side, quantity, price, fee, order_id, corr_id in trades_data:
        portfolio.add_trade(trade_id, symbol, side, quantity, price, fee, order_id, corr_id)
    
    # Update market prices
    portfolio.update_market_prices({
        "BTCUSDT": 51000.0,
        "ETHUSDT": 3100.0
    })
    
    # Show positions
    print("Current Positions:")
    for pos in portfolio.get_all_positions():
        print(f"  {pos['symbol']}: {pos['quantity']} @ ${pos['average_price']:.2f} "
              f"(Current: ${pos['current_price']:.2f}, PnL: ${pos['total_pnl']:.2f})")
    
    # Show stats
    stats = portfolio.get_portfolio_stats()
    print(f"\nPortfolio Stats:")
    for key, value in stats.items():
        if isinstance(value, float):
            if 'value' in key or 'pnl' in key or 'fee' in key:
                print(f"  {key}: ${value:.2f}")
            elif 'rate' in key:
                print(f"  {key}: {value:.1%}")
            else:
                print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")
    
    # Show trade history
    print(f"\nTrade History (last 5):")
    for trade in portfolio.get_trade_history(limit=5):
        print(f"  {trade['timestamp']}: {trade['side']} {trade['quantity']} {trade['symbol']} @ ${trade['price']:.2f}")
    
    print(f"\nPortfolio JSON export available via portfolio.export_to_json()")


if __name__ == "__main__":
    demo_portfolio_management()


# ============================================================================
# Exports for external use
# ============================================================================
__all__ = [
    'Base',
    'PositionORM',
    'TradeORM',
    'PortfolioManager',
    'demo_portfolio_management'
]
