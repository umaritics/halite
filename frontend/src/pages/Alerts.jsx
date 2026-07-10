import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { alertsAPI, decisionsAPI } from '../api/client';
import AlertBanner from '../components/AlertBanner';

export default function Alerts() {
  const [alerts, setAlerts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchAlerts = async () => {
    setLoading(true);
    try {
      const { data } = await alertsAPI.list();
      setAlerts(data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlerts();
  }, []);

  const handleAcknowledge = async (decision) => {
    await alertsAPI.acknowledge(decision.id);
    fetchAlerts();
  };

  const handleInvalidate = async (decision) => {
    const note = prompt('Invalidation note:');
    if (!note) return;
    await decisionsAPI.invalidate(decision.id, note);
    fetchAlerts();
  };

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-theme px-6 py-4">
        <h2 className="font-brand text-xl text-primary">Invalidation Alerts</h2>
        <p className="font-sans text-sm text-secondary">
          Decisions flagged when code changes may have invalidated prior reasoning
        </p>
      </header>

      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <p className="font-sans text-secondary">Loading alerts…</p>
        ) : alerts.length === 0 ? (
          <div className="halite-card mx-auto max-w-md p-8 text-center">
            <p className="font-sans text-secondary">No alerts — all decisions are up to date.</p>
            <p className="mt-2 font-sans text-xs text-[#555555]">
              Try syncing Gitea with a repo that modifies tracked component files.
            </p>
          </div>
        ) : (
          <div className="mx-auto max-w-3xl space-y-4">
            {alerts.map((alert) => (
              <AlertBanner
                key={alert.decision.id}
                alert={alert}
                onView={() => navigate('/app/decisions')}
                onAcknowledge={handleAcknowledge}
                onInvalidate={handleInvalidate}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
