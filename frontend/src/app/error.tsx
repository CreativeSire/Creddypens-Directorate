"use client";

export default function Error({
  error,
  reset,
}: {
  error: Error;
  reset: () => void;
}) {
  return (
    <div className="min-h-screen bg-[#0A0F14] text-white flex items-center justify-center p-4">
      <div className="border border-red-500/40 bg-red-500/10 p-8 max-w-md w-full">
        <div className="text-xs text-red-300 tracking-[0.25em] mb-2">{"// SYSTEM ERROR"}</div>
        <h2 className="text-2xl font-semibold mb-3">Something went wrong</h2>
        <p className="text-sm text-white/70 mb-6">{error.message || "An unexpected error occurred."}</p>
        <button
          onClick={reset}
          className="w-full px-4 py-3 bg-[#FFB800] text-[#0A0F14] font-bold hover:bg-[#FFB800]/90"
        >
          TRY AGAIN
        </button>
      </div>
    </div>
  );
}
