import { useId, type ComponentProps, type ReactNode } from 'react';
import { cn } from '@/lib/utils';

export function Field({ label, className, ...props }: ComponentProps<'input'> & { label: string }) {
  const id = useId();
  return <label htmlFor={id} className={cn('flex min-w-0 flex-col gap-1 text-caption', className)}>
    <span>{label}</span>
    <input id={id} {...props} className="h-9 min-w-0 rounded-md border border-input bg-background px-3 text-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
  </label>;
}

export function Area({ label, ...props }: ComponentProps<'textarea'> & { label: string }) {
  const id = useId();
  return <label htmlFor={id} className="flex min-w-0 flex-col gap-1 text-caption">
    <span>{label}</span>
    <textarea id={id} {...props} className="min-h-16 resize-y rounded-md border border-input bg-background px-3 py-2 text-body focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring" />
  </label>;
}

export function Panel({ title, children, className }: { title: string; children: ReactNode; className?: string }) {
  return <section aria-label={title} className={cn('flex min-w-0 flex-col gap-3 rounded-leaf bg-card p-4 shadow-card', className)}>
    <h2 className="text-title font-semibold">{title}</h2>{children}
  </section>;
}

export function Segmented<T extends string>({ label, value, options, onChange }: {
  label: string; value: T; options: { value: T; label: string }[]; onChange(value: T): void;
}) {
  return <fieldset className="min-w-0">
    <legend className="mb-1 text-caption">{label}</legend>
    <div className="flex overflow-hidden rounded-md border border-input">
      {options.map(option => <label key={option.value} className={cn('relative flex h-9 flex-1 cursor-pointer items-center justify-center text-caption', value === option.value ? 'bg-primary text-primary-foreground' : 'bg-background')}>
        <input className="absolute inset-0 cursor-pointer opacity-0 focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-ring" type="radio" name={label} value={option.value} checked={value === option.value} onChange={() => onChange(option.value)} />
        <span>{option.label}</span>
      </label>)}
    </div>
  </fieldset>;
}

export function Skeleton({ label }: { label: string }) {
  return <div role="status" aria-label={label} className="space-y-3 py-2">
    {[0, 1, 2, 3].map(i => <div key={i} className="h-4 animate-pulse rounded-sm bg-muted" />)}
    <span className="sr-only">{label}</span>
  </div>;
}
