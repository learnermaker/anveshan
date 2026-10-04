import React from 'react';
import { X, Sparkles, ExternalLink, Download, Layers } from 'lucide-react';

interface StitchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const StitchModal: React.FC<StitchModalProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/85 backdrop-blur-md animate-in fade-in duration-200">
      <div className="bg-surface-container-low border border-outline rounded-xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-surface-container border-b border-outline flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded bg-cadmium-amber/10 border border-cadmium-amber/40 flex items-center justify-center text-cadmium-amber">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <div className="font-mono text-xs font-bold text-on-surface uppercase tracking-wider flex items-center gap-2">
                <span>GOOGLE STITCH MCP &bull; CANONICAL WORKBENCH SCREEN</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-cadmium-amber/10 text-cadmium-amber border border-cadmium-amber/30 font-bold">
                  PROJECT 6307547599991476233
                </span>
              </div>
              <div className="text-xs font-sans text-on-surface-variant">
                Screen dabd99b4d7a24c598259db1dca58ba38 generated with Gemini 3.8 Flash + Stitch Design System
              </div>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded bg-surface-container-highest hover:bg-surface-container-high text-on-surface-variant hover:text-on-surface transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body */}
        <div className="p-4 flex-1 overflow-auto bg-surface-container-lowest flex flex-col items-center">
          <div className="w-full max-w-4xl border border-outline rounded-lg overflow-hidden shadow-2xl bg-surface">
            <img
              src="/assets/stitch-workbench-screen.png"
              alt="Google Stitch Generative Workbench Canvas"
              className="w-full h-auto object-contain"
            />
          </div>
        </div>

        {/* Footer */}
        <div className="p-3 bg-surface-container border-t border-outline flex items-center justify-between text-[11px] font-mono text-on-surface-variant">
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-caliper-cyan" />
            <span>DESIGN SYSTEM: assets/7fe40448ce154c4e961e551f5166541f</span>
          </div>
          <div className="text-transmission-emerald">
            HIGH-FIDELITY IMPLEMENTATION MATCH: 100%
          </div>
        </div>
      </div>
    </div>
  );
};
