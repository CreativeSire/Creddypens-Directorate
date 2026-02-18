import type { LucideIcon } from "lucide-react";

type EmptyStateProps = {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
};

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-14 px-6 text-center border border-cyan/20 bg-cyan/5">
      {Icon ? (
        <div className="w-14 h-14 text-cyan/35 mb-5">
          <Icon className="w-full h-full" strokeWidth={1.5} />
        </div>
      ) : null}
      <h3 className="text-xl font-bold text-white mb-2">{title}</h3>
      <p className="text-white/60 max-w-md leading-relaxed mb-6">{description}</p>
      {action ? (
        <button
          onClick={action.onClick}
          className="bg-amber text-void font-bold px-6 py-3 hover:bg-amber/90 hover:scale-105 active:scale-95 transition-all focus-ring"
        >
          {action.label}
        </button>
      ) : null}
    </div>
  );
}

