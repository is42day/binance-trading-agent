interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  valueClass?: string;
}

export default function MetricCard({ title, value, subtitle, valueClass }: MetricCardProps) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <p className="text-gray-400 text-sm mb-1">{title}</p>
      <p className={`text-2xl font-bold ${valueClass ?? 'text-white'}`}>{value}</p>
      {subtitle && <p className="text-gray-500 text-xs mt-1">{subtitle}</p>}
    </div>
  );
}
