#!/usr/bin/env python3
"""
MCP Client for Binance Trading Agent
Interactive client to test trading agent functionality
"""
import asyncio
import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, '/app')

from mcp_server import server

class TradingMCPClient:
    def __init__(self):
        self.server = server
    
    async def test_market_data(self, symbol="BTCUSDT"):
        """Test market data retrieval"""
        print(f"\n🔍 Getting market data for {symbol}...")
        result = await self.server.get_market_data(symbol)
        print(json.dumps(result, indent=2))
        return result
    
    async def test_trading_signal(self, symbol="BTCUSDT", indicator="rsi"):
        """Test trading signal generation"""
        print(f"\n📊 Computing {indicator.upper()} signal for {symbol}...")
        result = await self.server.compute_trading_signal(symbol, indicator)
        print(json.dumps(result, indent=2))
        return result
    
    async def test_risk_validation(self):
        """Test risk management validation"""
        print(f"\n⚖️ Testing risk validation...")
        
        # Sample data for validation
        signal = {
            "symbol": "BTCUSDT",
            "side": "BUY", 
            "quantity": 0.001,
            "signal": "BUY",
            "confidence": 0.8
        }
        
        portfolio = {
            "positions": {},
            "active_trades": [],
            "max_position": 10,
            "drawdown": 0.05,
            "max_drawdown": 0.2
        }
        
        market_data = {"price": 45000.0}
        
        result = await self.server.validate_trade(signal, portfolio, market_data)
        print(json.dumps(result, indent=2))
        return result
    
    async def test_account_balance(self, asset="USDT"):
        """Test account balance retrieval"""
        print(f"\n💰 Getting {asset} balance...")
        result = await self.server.get_account_balance(asset)
        print(json.dumps(result, indent=2))
        return result
    
    async def test_order_placement(self, symbol="BTCUSDT", dry_run=True):
        """Test order placement (dry run by default)"""
        print(f"\n🛒 Testing order placement for {symbol}...")
        if dry_run:
            print("⚠️  DRY RUN MODE - No actual order will be placed")
            result = {"message": "Dry run - order would be placed", "symbol": symbol}
        else:
            result = await self.server.place_order(symbol, "BUY", "MARKET", 0.001)
        
        print(json.dumps(result, indent=2))
        return result
    
    async def run_full_workflow(self, symbol="BTCUSDT"):
        """Run complete trading workflow"""
        print(f"\n🚀 Running full trading workflow for {symbol}...")
        print("=" * 60)
        
        try:
            # 1. Get market data
            market_data = await self.test_market_data(symbol)
            if "error" in market_data:
                print("❌ Market data failed, stopping workflow")
                return
            
            # 2. Generate trading signal
            signal = await self.test_trading_signal(symbol, "rsi")
            if "error" in signal:
                print("❌ Signal generation failed, stopping workflow")
                return
            
            # 3. Check account balance
            balance = await self.test_account_balance("USDT")
            if "error" in balance:
                print("❌ Balance check failed, stopping workflow")
                return
            
            # 4. Validate trade
            portfolio = {
                "positions": {},
                "active_trades": [],
                "max_position": 10,
                "drawdown": 0.05,
                "max_drawdown": 0.2
            }
            
            validation = await self.server.validate_trade(
                {**signal, "symbol": symbol, "quantity": 0.001}, 
                portfolio, 
                market_data
            )
            
            print(f"\n⚖️ Trade validation result:")
            print(json.dumps(validation, indent=2))
            
            # 5. Place order (dry run)
            if validation.get("valid", False):
                print(f"\n✅ Trade validated - proceeding with dry run order")
                await self.test_order_placement(symbol, dry_run=True)
            else:
                print(f"\n❌ Trade validation failed - no order placed")
            
            print("\n🎉 Workflow completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Workflow failed: {str(e)}")

async def main():
    """Interactive MCP client main function"""
    client = TradingMCPClient()
    
    print("🤖 Binance Trading Agent MCP Client")
    print("=" * 50)
    
    while True:
        print(f"\nAvailable commands:")
        print("1. Test market data")
        print("2. Test trading signal") 
        print("3. Test risk validation")
        print("4. Test account balance")
        print("5. Test order placement (dry run)")
        print("6. Run full workflow")
        print("0. Exit")
        
        try:
            choice = input(f"\nEnter your choice (0-6): ").strip()
            
            if choice == "0":
                print("👋 Goodbye!")
                break
            elif choice == "1":
                symbol = input("Enter symbol (default BTCUSDT): ").strip() or "BTCUSDT"
                await client.test_market_data(symbol)
            elif choice == "2":
                symbol = input("Enter symbol (default BTCUSDT): ").strip() or "BTCUSDT"
                indicator = input("Enter indicator (rsi/macd, default rsi): ").strip() or "rsi"
                await client.test_trading_signal(symbol, indicator)
            elif choice == "3":
                await client.test_risk_validation()
            elif choice == "4":
                asset = input("Enter asset (default USDT): ").strip() or "USDT"
                await client.test_account_balance(asset)
            elif choice == "5":
                symbol = input("Enter symbol (default BTCUSDT): ").strip() or "BTCUSDT"
                await client.test_order_placement(symbol, dry_run=True)
            elif choice == "6":
                symbol = input("Enter symbol (default BTCUSDT): ").strip() or "BTCUSDT"
                await client.run_full_workflow(symbol)
            else:
                print("❌ Invalid choice, please try again")
                
        except KeyboardInterrupt:
            print(f"\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())