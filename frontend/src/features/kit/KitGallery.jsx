import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  ConfirmDialog,
  EmptyState,
  ErrorBoundary,
  ErrorCard,
  PageHeader,
  Skeleton,
  Tabs,
} from '../../components/ui';
import { useTheme } from '../../context/ThemeContext';

function Section({ title, children }) {
  return (
    <section className="space-y-3">
      <h2 className="font-brand text-lg text-primary">{title}</h2>
      <div className="flex flex-wrap items-start gap-3">{children}</div>
    </section>
  );
}

function Bomb() {
  throw new Error('Gallery test error');
}

const VARIANTS = ['primary', 'outline', 'ghost', 'danger'];
const TONES = ['neutral', 'accent', 'success', 'warning', 'danger'];

export default function KitGallery() {
  const theme = useTheme();
  const [dialog, setDialog] = useState(null);
  const [resetKey, setResetKey] = useState(0);
  const [crash, setCrash] = useState(false);

  const tabs = [
    { id: 'one', label: 'Overview', content: <p className="text-secondary">First panel.</p> },
    { id: 'two', label: 'Details', content: <p className="text-secondary">Second panel.</p> },
    { id: 'three', label: 'History', content: <p className="text-secondary">Third panel.</p> },
  ];

  return (
    <div className="h-full space-y-8 overflow-y-auto p-6">
      <PageHeader
        title="UI kit gallery"
        description="Development only. Every component in every variant and state."
        actions={
          theme?.toggleTheme && (
            <Button variant="outline" onClick={theme.toggleTheme}>
              Toggle theme
            </Button>
          )
        }
      />

      {['md', 'sm'].map(size => (
        <Section key={size} title={`Buttons, size ${size}`}>
          {VARIANTS.map(variant => (
            <Button key={variant} variant={variant} size={size}>{variant}</Button>
          ))}
          {VARIANTS.map(variant => (
            <Button key={`l-${variant}`} variant={variant} size={size} loading>
              {variant} loading
            </Button>
          ))}
          {VARIANTS.map(variant => (
            <Button key={`d-${variant}`} variant={variant} size={size} disabled>
              {variant} disabled
            </Button>
          ))}
        </Section>
      ))}

      <Section title="Badges">
        {TONES.map(tone => <Badge key={tone} tone={tone}>{tone}</Badge>)}
      </Section>

      <Section title="Tabs">
        <div className="w-full"><Tabs tabs={tabs} label="Gallery tabs" /></div>
      </Section>

      <Section title="Cards">
        <Card title="Card with title">Body text inside a card.</Card>
        <Card>Card without a title.</Card>
      </Section>

      <Section title="Error card">
        <ErrorCard message="Something failed to load." onRetry={() => {}} />
        <ErrorCard message="An error with no retry action." />
      </Section>

      <Section title="Empty state">
        <EmptyState title="Nothing here yet" body="Records will appear once they exist." />
        <EmptyState
          title="With an action"
          body="Create the first one."
          action={<Button size="sm">Create</Button>}
        />
      </Section>

      <Section title="Skeletons">
        <Skeleton className="w-64" />
        <Skeleton variant="card" className="w-64" />
      </Section>

      <Section title="Confirm dialog">
        <Button variant="outline" onClick={() => setDialog('default')}>Open default</Button>
        <Button variant="danger" onClick={() => setDialog('danger')}>Open danger</Button>
        <ConfirmDialog
          open={dialog !== null}
          title={dialog === 'danger' ? 'Delete this record?' : 'Continue?'}
          tone={dialog === 'danger' ? 'danger' : 'default'}
          confirmLabel={dialog === 'danger' ? 'Delete' : 'Confirm'}
          onConfirm={() => setDialog(null)}
          onCancel={() => setDialog(null)}
        >
          This is the dialog body text.
        </ConfirmDialog>
      </Section>

      <Section title="Error boundary">
        <Button variant="danger" onClick={() => setCrash(true)}>Trigger error</Button>
        <Button
          variant="outline"
          onClick={() => {
            setCrash(false);
            setResetKey(key => key + 1);
          }}
        >
          Reset boundary
        </Button>
        <div className="w-full">
          <ErrorBoundary resetKey={resetKey}>
            {crash ? <Bomb /> : <p className="text-secondary">Boundary is healthy.</p>}
          </ErrorBoundary>
        </div>
      </Section>
    </div>
  );
}
