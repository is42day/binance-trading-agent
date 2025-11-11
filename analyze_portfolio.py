#!/usr/bin/env python3
"""
Analyze portfolio database and trading results
"""
import sqlite3
import sys
from datetime import datetime

db_path = '/app/data/portfolio.db'

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    
    print("=" * 70)
    print("PORTFOLIO DATABASE ANALYSIS")
    print("=" * 70)
    print(f"\nDatabase: {db_path}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    if not tables:
        print("❌ No tables found in database")
        sys.exit(0)
    
    print(f"📊 Tables Found: {len(tables)}")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Try to get trades
    print("\n" + "=" * 70)
    print("TRADES")
    print("=" * 70)
    
    try:
        cursor.execute("SELECT COUNT(*) FROM trades")
        trade_count = cursor.fetchone()[0]
        print(f"\n✅ Total Trades: {trade_count}")
        
        if trade_count > 0:
            cursor.execute("""
                SELECT 
                    trade_id, symbol, side, quantity, price, 
                    fee, timestamp, correlation_id
                FROM trades 
                ORDER BY timestamp DESC 
                LIMIT 20
            """)
            trades = cursor.fetchall()
            
            print(f"\n📈 Last {min(len(trades), 20)} Trades:\n")
            print(f"{'Trade ID':<20} {'Symbol':<12} {'Side':<6} {'Qty':<10} {'Price':<12} {'Fee':<8} {'Time':<19}")
            print("-" * 100)
            
            for trade in trades:
                trade_id, symbol, side, qty, price, fee, ts, corr_id = trade
                print(f"{str(trade_id):<20} {symbol:<12} {side:<6} {qty:<10.6f} ${price:<11,.2f} ${fee:<7,.4f} {ts}")
        
    except Exception as e:
        print(f"❌ Error querying trades table: {str(e)}")
    
    # Try to get positions
    print("\n" + "=" * 70)
    print("POSITIONS")
    print("=" * 70)
    
    try:
        cursor.execute("SELECT COUNT(*) FROM positions")
        pos_count = cursor.fetchone()[0]
        print(f"\n✅ Total Positions: {pos_count}")
        
        if pos_count > 0:
            cursor.execute("""
                SELECT 
                    symbol, side, quantity, entry_price, 
                    current_price, pnl, timestamp
                FROM positions 
                ORDER BY timestamp DESC
            """)
            positions = cursor.fetchall()
            
            print(f"\n📊 Positions:\n")
            print(f"{'Symbol':<12} {'Side':<6} {'Qty':<12} {'Entry Price':<14} {'Current Price':<14} {'P&L':<12} {'Time':<19}")
            print("-" * 100)
            
            total_pnl = 0
            for pos in positions:
                symbol, side, qty, entry, current, pnl, ts = pos
                total_pnl += pnl if pnl else 0
                pnl_str = f"${pnl:,.2f}" if pnl else "N/A"
                print(f"{symbol:<12} {side:<6} {qty:<12.6f} ${entry:<13,.2f} ${current:<13,.2f} {pnl_str:<12} {ts}")
            
            print(f"\n📊 Total Portfolio P&L: ${total_pnl:,.2f}")
        
    except Exception as e:
        print(f"❌ Error querying positions table: {str(e)}")
    
    # Get summary stats
    print("\n" + "=" * 70)
    print("SUMMARY STATISTICS")
    print("=" * 70)
    
    try:
        cursor.execute("SELECT COUNT(*) FROM trades WHERE side='BUY'")
        buy_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM trades WHERE side='SELL'")
        sell_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(quantity * price) FROM trades WHERE side='BUY'")
        total_buy = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(quantity * price) FROM trades WHERE side='SELL'")
        total_sell = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(fee) FROM trades")
        total_fees = cursor.fetchone()[0] or 0
        
        print(f"\nBuy Orders: {buy_count}")
        print(f"Sell Orders: {sell_count}")
        print(f"Total Buy Volume: ${total_buy:,.2f}")
        print(f"Total Sell Volume: ${total_sell:,.2f}")
        print(f"Total Fees Paid: ${total_fees:,.2f}")
        
        win_loss_ratio = buy_count / sell_count if sell_count > 0 else 0
        print(f"Buy/Sell Ratio: {win_loss_ratio:.2f}")
        
    except Exception as e:
        print(f"❌ Error getting summary stats: {str(e)}")
    
    print("\n" + "=" * 70)
    
    conn.close()
    
except sqlite3.OperationalError as e:
    print(f"❌ Database Error: {str(e)}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {str(e)}")
    sys.exit(1)
