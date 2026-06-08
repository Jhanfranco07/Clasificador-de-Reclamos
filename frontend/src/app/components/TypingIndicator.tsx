export default function TypingIndicator() {
  return (
    <div className="flex justify-start" aria-label="SmartClaim AI está escribiendo">
      <div className="rounded-lg bg-gray-100 px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 150, 300].map((delay) => (
            <span
              key={delay}
              className="size-2 animate-bounce rounded-full bg-gray-500"
              style={{ animationDelay: `${delay}ms` }}
            />
          ))}
        </div>
        <p className="mt-1 text-[11px] text-gray-500">SmartClaim AI está escribiendo...</p>
      </div>
    </div>
  );
}
