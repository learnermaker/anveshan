/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Service base URL; '' = same origin; 'mock' = canned SYNTHETIC fixtures in the browser. */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

/** lucide-react 0.475.0 ships without a root .d.ts; declare the module so TypeScript compiles. */
declare module 'lucide-react' {
  import type { FC, SVGProps } from 'react';
  export type LucideProps = SVGProps<SVGSVGElement> & { size?: number | string; strokeWidth?: number | string; absoluteStrokeWidth?: boolean; color?: string; className?: string };
  export type LucideIcon = FC<LucideProps>;
  // All icons used in this project
  export const Activity: LucideIcon;
  export const AlertTriangle: LucideIcon;
  export const ArrowLeft: LucideIcon;
  export const ArrowRight: LucideIcon;
  export const Award: LucideIcon;
  export const Check: LucideIcon;
  export const CheckCircle2: LucideIcon;
  export const ChevronDown: LucideIcon;
  export const ChevronLeft: LucideIcon;
  export const ChevronRight: LucideIcon;
  export const ChevronUp: LucideIcon;
  export const Clock: LucideIcon;
  export const Compass: LucideIcon;
  export const Copy: LucideIcon;
  export const Cpu: LucideIcon;
  export const Crosshair: LucideIcon;
  export const Download: LucideIcon;
  export const Droplets: LucideIcon;
  export const Dumbbell: LucideIcon;
  export const Eraser: LucideIcon;
  export const ExternalLink: LucideIcon;
  export const Eye: LucideIcon;
  export const FastForward: LucideIcon;
  export const FileCheck: LucideIcon;
  export const FileCheck2: LucideIcon;
  export const FileCode: LucideIcon;
  export const FileText: LucideIcon;
  export const FileUp: LucideIcon;
  export const Film: LucideIcon;
  export const Fingerprint: LucideIcon;
  export const GitBranch: LucideIcon;
  export const Grid: LucideIcon;
  export const HelpCircle: LucideIcon;
  export const Info: LucideIcon;
  export const Layers: LucideIcon;
  export const Loader2: LucideIcon;
  export const Lock: LucideIcon;
  export const MessageSquareQuote: LucideIcon;
  export const MessageSquareText: LucideIcon;
  export const MessageSquare: LucideIcon;
  export const Music: LucideIcon;
  export const Pencil: LucideIcon;
  export const Pause: LucideIcon;
  export const Play: LucideIcon;
  export const Plus: LucideIcon;
  export const PlusCircle: LucideIcon;
  export const Radio: LucideIcon;
  export const RefreshCw: LucideIcon;
  export const Repeat: LucideIcon;
  export const Rewind: LucideIcon;
  export const RotateCcw: LucideIcon;
  export const Save: LucideIcon;
  export const Scissors: LucideIcon;
  export const Search: LucideIcon;
  export const Send: LucideIcon;
  export const Settings: LucideIcon;
  export const Shield: LucideIcon;
  export const ShieldAlert: LucideIcon;
  export const ShieldCheck: LucideIcon;
  export const Sliders: LucideIcon;
  export const Sparkles: LucideIcon;
  export const Target: LucideIcon;
  export const TrendingUp: LucideIcon;
  export const Undo2: LucideIcon;
  export const Upload: LucideIcon;
  export const UploadCloud: LucideIcon;
  export const UserCheck: LucideIcon;
  export const Video: LucideIcon;
  export const Volume2: LucideIcon;
  export const Wand2: LucideIcon;
  export const Wrench: LucideIcon;
  export const X: LucideIcon;
  export const Zap: LucideIcon;
}
