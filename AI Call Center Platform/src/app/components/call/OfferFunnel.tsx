import { CheckCircle2, XCircle, ArrowRightCircle } from 'lucide-react';
import { OfferDetail } from '../../lib/types';
import { cn } from '../ui/utils';

interface OfferFunnelProps {
  presented: string[];
  skipped: string[];
  details: OfferDetail[];
}

export function OfferFunnel({ presented, skipped, details }: OfferFunnelProps) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 mb-5">
      <h3 className="text-foreground text-sm font-semibold mb-4">Offer Presentation Funnel</h3>
      
      <div className="space-y-3">
        {details.map((offer) => (
          <div 
            key={`${offer.offer_name}-${offer.presented ? 'presented' : 'skipped'}-${offer.skip_reason || 'none'}`} 
            className={cn(
              "flex items-center justify-between p-3 rounded-lg border",
              offer.presented ? "bg-emerald-500/5 border-emerald-500/10" : 
              offer.skip_reason ? "bg-amber-500/5 border-amber-500/10" : "bg-red-500/5 border-red-500/10"
            )}
          >
            <div className="flex items-center gap-3">
              {offer.presented ? (
                <CheckCircle2 size={16} className="text-emerald-500" />
              ) : offer.skip_reason ? (
                <ArrowRightCircle size={16} className="text-amber-500" />
              ) : (
                <XCircle size={16} className="text-red-500" />
              )}
              
              <div>
                <p className="text-xs font-semibold text-foreground">{offer.offer_name}</p>
                <p className="text-[10px] text-muted-foreground">
                  {offer.presented ? "Presented to customer" : 
                   offer.skip_reason ? `Skipped: ${offer.skip_reason}` : "Incorrectly skipped"}
                </p>
              </div>
            </div>

            <div className="flex gap-1">
              {offer.qualifying_questions_asked && (
                <span className="text-[9px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-md">Qualifying OK</span>
              )}
              {offer.branch_followed_correctly && (
                <span className="text-[9px] px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 rounded-md">Branch OK</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
