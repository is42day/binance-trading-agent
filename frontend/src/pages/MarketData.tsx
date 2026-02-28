import { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { useMarketPrice } from '../hooks/useApi';
import type { MarketPrice } from '../types';
import LoadingSpinner from '../components/LoadingSpinner';
import ErrorMessage from '../components/ErrorMessage';

const SYMBOLS = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'ADAUSDT'];

interface PricePoint {
  time: string;
  price: number;
}

function fmt(n: number | undefined) {
  if (n === undefined || n === null) return 'N/A';
  return n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 8 });
}

export default function MarketData() {
  const [symbol, setSymbol] = useState('BTCUSDT');
  const [priceHistory, setPriceHistory] = useState<PricePoint[]>([]);

  const { data: market, isLoading, isError } = useMarketPrice(symbol);

  useEffect(() => {
    if (market?.price) {
      setPriceHistory(prev => {
        const now = new Date().toLocaleTimeString();
        const next = [...prev, { time: now, price: market.price }];
        return next.slice(-20);
      });
    }
  }, [market?.price]);

  // reset history when symbol changes
  useEffect(() => {
    setPriceHistory([]);
  }, [symbol]);

  const change = (market as (MarketPrice & { change_percent_24h?: number }) | undefined)?.change_percent_24h;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-white">Market Data</h2>

      <div className="flex items-center gap-4">
        <label className="text-gray-400 text-sm">Symbol:</label>
        <select
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          className="bg-gray-800 border border-gray-600 text-white rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500"
        >
          {SYMBOLS.map(s => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>

      {isLoading ? (
        <LoadingSpinner />
      ) : isError ? (
        <ErrorMessage />
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <p className="text-gray-400 text-sm">{symbol} Price</p>
            <p className="text-3xl font-bold text-white mt-1">${fmt(market?.price)}</p>
          </div>
          <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
            <p className="text-gray-400 text-sm">24h Change</p>
            <p className={`text-3xl font-bold mt-1 ${(change ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {change !== undefined ? `${change >= 0 ? '+' : ''}${change.toFixed(2)}%` : 'N/A'}
            </p>
          </div>
        </div>
      )}

      <div className="bg-gray-800 rounded-lg border border-gray-700 p-4">
        <h3 className="text-lg font-semibold text-white mb-4">Price Trend (last 20 readings)</h3>
        {priceHistory.length < 2 ? (
          <div className="flex items-center justify-center h-48 text-gray-500 text-sm">
            Collecting price data... (refreshes every 10s)
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <LineChart data={priceHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis dataKey="time" tick={{ fill: '#9CA3AF', fontSize: 10 }} />
              <YAxis
                tick={{ fill: '#9CA3AF', fontSize: 10 }}
                domain={['auto', 'auto']}
                tickFormatter={v => `$${v.toLocaleString()}`}
                width={80}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#1F2937', border: '1px solid #374151', borderRadius: 8 }}
                labelStyle={{ color: '#9CA3AF' }}
                itemStyle={{ color: '#60A5FA' }}
                formatter={(v) => [`$${fmt(v as number)}`, 'Price']}
              />
              <Line type="monotone" dataKey="price" stroke="#3B82F6" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
