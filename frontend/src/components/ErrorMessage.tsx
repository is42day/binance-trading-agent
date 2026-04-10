interface ErrorMessageProps {
  message?: string;
}

export default function ErrorMessage({ message }: ErrorMessageProps) {
  return (
    <div className="flex items-center justify-center h-32">
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4 text-red-400 text-sm">
        ⚠️ {message ?? 'Failed to load data. Please check that the API is running.'}
      </div>
    </div>
  );
}
