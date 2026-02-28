import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import MarketData from './pages/MarketData';
import PaperTrading from './pages/PaperTrading';
import SignalsRisk from './pages/SignalsRisk';
import Performance from './pages/Performance';
import SystemHealth from './pages/SystemHealth';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 10_000,
      retry: 1,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="market" element={<MarketData />} />
            <Route path="paper-trading" element={<PaperTrading />} />
            <Route path="signals" element={<SignalsRisk />} />
            <Route path="performance" element={<Performance />} />
            <Route path="health" element={<SystemHealth />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
