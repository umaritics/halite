import React, { useCallback, useEffect, useState } from 'react';
import { adminAPI } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { formatDate, formatDateTime } from '../../utils/format';
import { formatDetail } from '../../utils/diagnostics';
import { describeLoadError } from '../../utils/loadError';
import { Button, ConfirmDialog, ErrorCard, PageHeader, Skeleton } from '../../components/ui';

const ROLES = [
  { value: 'technician', label: 'Technician' },
  { value: 'supervisor', label: 'Supervisor' },
  { value: 'admin', label: 'Administrator' },
];

const ROLE_LABELS = Object.fromEntries(ROLES.map((r) => [r.value, r.label]));

function confirmTitle(pending) {
  if (pending?.kind === 'role') return 'Change role?';
  if (pending?.kind === 'deactivate') return 'Deactivate account?';
  return 'Revoke invitation?';
}

function confirmLabel(pending) {
  if (pending?.kind === 'role') return 'Change role';
  if (pending?.kind === 'deactivate') return 'Deactivate';
  return 'Revoke invitation';
}

function confirmBody(pending) {
  if (!pending) return null;
  if (pending.kind === 'role') {
    const { member, nextRole } = pending;
    return `Change ${member.email} from ${ROLE_LABELS[member.role] || member.role} to ${ROLE_LABELS[nextRole] || nextRole}? Their access changes immediately.`;
  }
  if (pending.kind === 'deactivate') {
    return `${pending.member.email} will not be able to sign in until the account is reactivated.`;
  }
  return `The activation link sent to ${pending.invite.email} will stop working.`;
}

export default function TeamAccess() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [invites, setInvites] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [auditLoading, setAuditLoading] = useState(true);
  const [auditError, setAuditError] = useState(null);

  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteName, setInviteName] = useState('');
  const [inviteRole, setInviteRole] = useState('technician');
  const [creatingInvite, setCreatingInvite] = useState(false);
  const [createdInviteLink, setCreatedInviteLink] = useState('');
  const [copied, setCopied] = useState(false);
  const [actionError, setActionError] = useState(null);
  // The change waiting for confirmation: { kind: 'role' | 'deactivate' | 'revoke', ... }
  const [pending, setPending] = useState(null);
  const [confirming, setConfirming] = useState(false);

  const loadPeople = useCallback(async () => {
    setLoadError(null);
    try {
      const [usersRes, invitesRes] = await Promise.all([
        adminAPI.listUsers(),
        adminAPI.listInvites(),
      ]);
      setUsers(usersRes.data || []);
      setInvites(invitesRes.data || []);
    } catch (err) {
      setLoadError(describeLoadError(err).message);
    } finally {
      setLoading(false);
    }
  }, []);

  // The audit log loads on its own so a failure here is reported as a failure,
  // not shown as an empty log, and does not hide the member list.
  const loadAudit = useCallback(async () => {
    setAuditError(null);
    try {
      const res = await adminAPI.auditEvents({ limit: 40 });
      setAuditEvents(res.data?.items || []);
    } catch (err) {
      setAuditError(describeLoadError(err).message);
    } finally {
      setAuditLoading(false);
    }
  }, []);

  const loadWorkspaceData = useCallback(
    () => Promise.all([loadPeople(), loadAudit()]),
    [loadPeople, loadAudit],
  );

  const retryPeople = () => {
    setLoading(true);
    loadPeople();
  };

  const retryAudit = () => {
    setAuditLoading(true);
    loadAudit();
  };

  useEffect(() => {
    loadWorkspaceData();
  }, [loadWorkspaceData]);

  const handleCreateInvite = async (e) => {
    e.preventDefault();
    if (creatingInvite) return;
    setCreatingInvite(true);
    setActionError(null);
    setCreatedInviteLink('');
    setCopied(false);
    try {
      const { data } = await adminAPI.createInvite({
        email: inviteEmail.trim(),
        full_name: inviteName.trim(),
        role: inviteRole,
      });
      const origin = window.location.origin;
      setCreatedInviteLink(`${origin}${data.invite_path}`);
      setInviteEmail('');
      setInviteName('');
      await loadWorkspaceData();
    } catch (err) {
      setActionError(formatDetail(err?.response?.data?.detail) || 'Could not create invitation.');
    } finally {
      setCreatingInvite(false);
    }
  };

  const handleCopyInvite = async () => {
    if (!createdInviteLink) return;
    try {
      await navigator.clipboard.writeText(createdInviteLink);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const runConfirmedAction = async () => {
    if (!pending || confirming) return;
    setConfirming(true);
    setActionError(null);
    try {
      if (pending.kind === 'role') {
        await adminAPI.updateUser(pending.member.id, { role: pending.nextRole });
      } else if (pending.kind === 'deactivate') {
        await adminAPI.updateUser(pending.member.id, { is_active: false });
      } else {
        await adminAPI.revokeInvite(pending.invite.id);
      }
      await loadWorkspaceData();
    } catch (err) {
      setActionError(formatDetail(err?.response?.data?.detail) || pending.failureMessage);
    } finally {
      setConfirming(false);
      setPending(null);
    }
  };

  const askRoleChange = (member, nextRole) => {
    if (nextRole === member.role) return;
    setPending({
      kind: 'role',
      member,
      nextRole,
      failureMessage: 'Could not update user role.',
    });
  };

  const askDeactivate = (member) => {
    setPending({ kind: 'deactivate', member, failureMessage: 'Could not update account status.' });
  };

  const askRevoke = (invite) => {
    setPending({ kind: 'revoke', invite, failureMessage: 'Could not revoke invitation.' });
  };

  const handleReactivate = async (member) => {
    setActionError(null);
    try {
      await adminAPI.updateUser(member.id, { is_active: true });
      await loadWorkspaceData();
    } catch (err) {
      setActionError(formatDetail(err?.response?.data?.detail) || 'Could not update account status.');
    }
  };

  const pendingInvites = invites.filter((inv) => !inv.accepted_at && !inv.revoked_at);

  return (
    <div className="h-full overflow-y-auto">
      <div className="mx-auto max-w-5xl space-y-6 p-6">
        <PageHeader
          title="Team & Access"
          description="Invite authorised members, manage role permissions, and inspect security and review audit events"
        />

        {actionError && (
          <div
            role="alert"
            className="rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 font-sans text-sm text-red-400"
          >
            {actionError}
          </div>
        )}

        {/* Issue single-use invite */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-lg text-primary">Invite a team member</h3>
          <p className="mt-1 font-sans text-xs text-secondary">
            Generates a single-use 72-hour activation link. Public self-registration is disabled.
          </p>

          <form onSubmit={handleCreateInvite} className="mt-4 grid gap-3 sm:grid-cols-[1.2fr_1fr_0.8fr_auto]">
            <input
              type="email"
              required
              placeholder="Work email"
              aria-label="Invite email"
              value={inviteEmail}
              onChange={(e) => setInviteEmail(e.target.value)}
              className="halite-input"
            />
            <input
              type="text"
              required
              placeholder="Full name"
              aria-label="Invite full name"
              value={inviteName}
              onChange={(e) => setInviteName(e.target.value)}
              className="halite-input"
            />
            <select
              aria-label="Invite role"
              value={inviteRole}
              onChange={(e) => setInviteRole(e.target.value)}
              className="halite-input"
            >
              {ROLES.map((r) => (
                <option key={r.value} value={r.value}>
                  {r.label}
                </option>
              ))}
            </select>
            <Button type="submit" disabled={creatingInvite} className="whitespace-nowrap">
              {creatingInvite ? 'Issuing…' : 'Create invite'}
            </Button>
          </form>

          {createdInviteLink && (
            <div className="mt-4 rounded-lg border border-accent/40 bg-accent/10 p-4">
              <p className="font-sans text-xs font-medium text-accent">
                Single-use activation link (shown once — share securely with the recipient):
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <code className="flex-1 break-all rounded bg-page px-3 py-2 font-mono text-xs text-primary border border-theme">
                  {createdInviteLink}
                </code>
                <Button variant="ghost" size="sm" onClick={handleCopyInvite}>
                  {copied ? 'Copied' : 'Copy link'}
                </Button>
              </div>
            </div>
          )}

          {pendingInvites.length > 0 && (
            <div className="mt-5 border-t border-theme pt-4">
              <h4 className="font-sans text-xs font-medium text-secondary mb-2">
                Pending invitations ({pendingInvites.length})
              </h4>
              <div className="divide-y divide-border-dark/40">
                {pendingInvites.map((inv) => (
                  <div key={inv.id} className="flex flex-wrap items-center justify-between gap-2 py-2.5 text-sm font-sans">
                    <div>
                      <span className="font-medium text-primary">{inv.full_name}</span>{' '}
                      <span className="font-mono text-xs text-secondary">{inv.email}</span>
                      <span className="ml-2 rounded bg-surface px-2 py-0.5 font-mono text-xs text-accent border border-theme">
                        {inv.role}
                      </span>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => askRevoke(inv)}>
                      Revoke
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Workspace Members */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-lg text-primary">Workspace members</h3>
          {loading ? (
            <Skeleton className="mt-4" lines={3} />
          ) : loadError ? (
            <div className="mt-4">
              <ErrorCard message={loadError} onRetry={retryPeople} />
            </div>
          ) : (
            <div className="mt-4 divide-y divide-border-dark/40">
              {users.map((member) => {
                const isSelf = member.id === currentUser?.id;
                return (
                  <div
                    key={member.id}
                    className="flex flex-wrap items-center justify-between gap-4 py-3 font-sans text-sm"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-primary">{member.full_name}</span>
                        {isSelf && (
                          <span className="rounded bg-accent/15 px-2 py-0.5 text-[11px] text-accent">You</span>
                        )}
                        {!member.is_active && (
                          <span className="rounded bg-red-500/15 px-2 py-0.5 text-[11px] text-red-400">
                            Deactivated
                          </span>
                        )}
                      </div>
                      <p className="font-mono text-xs text-secondary">{member.email}</p>
                      {member.last_login_at && (
                        <p className="text-xs text-secondary">Last sign-in: {formatDate(member.last_login_at)}</p>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <select
                        aria-label={`Role for ${member.email}`}
                        value={member.role}
                        disabled={isSelf}
                        onChange={(e) => askRoleChange(member, e.target.value)}
                        className="halite-input w-36 py-1.5 text-xs disabled:opacity-60"
                      >
                        {ROLES.map((r) => (
                          <option key={r.value} value={r.value}>
                            {r.label}
                          </option>
                        ))}
                      </select>

                      <Button
                        variant="ghost"
                        size="sm"
                        disabled={isSelf}
                        onClick={() => (member.is_active ? askDeactivate(member) : handleReactivate(member))}
                      >
                        {member.is_active ? 'Deactivate' : 'Reactivate'}
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>

        {/* Audit Log */}
        <section className="halite-card p-6">
          <h3 className="font-brand text-lg text-primary">Recent security &amp; review audit log</h3>
          <p className="mt-1 font-sans text-xs text-secondary">
            Append-only record of sign-ins, invitations, role changes, and conflict-queue adjudications.
          </p>

          {auditLoading ? (
            <Skeleton className="mt-4" lines={3} />
          ) : auditError ? (
            <div className="mt-4">
              <ErrorCard message={auditError} onRetry={retryAudit} />
            </div>
          ) : auditEvents.length === 0 ? (
            <p className="mt-3 font-sans text-sm text-secondary">No audit events recorded yet.</p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-left font-sans text-xs">
                <thead>
                  <tr className="border-b border-theme text-secondary">
                    <th className="py-2 pr-3 font-medium">When</th>
                    <th className="py-2 pr-3 font-medium">Event</th>
                    <th className="py-2 pr-3 font-medium">Actor</th>
                    <th className="py-2 pr-3 font-medium">Target</th>
                    <th className="py-2 font-medium">IP</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-dark/30">
                  {auditEvents.map((ev) => (
                    <tr key={ev.id}>
                      <td className="py-2 pr-3 font-mono text-secondary whitespace-nowrap">
                        {formatDateTime(ev.created_at)}
                      </td>
                      <td className="py-2 pr-3 font-mono text-primary">{ev.action}</td>
                      <td className="py-2 pr-3 text-primary">
                        {ev.actor_email || ev.actor_user_id || '—'}
                        {ev.actor_role && (
                          <span className="ml-1.5 font-mono text-[11px] text-secondary">({ev.actor_role})</span>
                        )}
                      </td>
                      <td className="py-2 pr-3 font-mono text-secondary">
                        {ev.target_id ? `${ev.target_type || 'item'}:${ev.target_id.slice(0, 18)}` : '—'}
                      </td>
                      <td className="py-2 font-mono text-secondary">{ev.ip_address || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </div>

      <ConfirmDialog
        open={Boolean(pending)}
        title={confirmTitle(pending)}
        confirmLabel={confirmLabel(pending)}
        tone={pending?.kind === 'role' ? 'default' : 'danger'}
        loading={confirming}
        onConfirm={runConfirmedAction}
        onCancel={() => setPending(null)}
      >
        {confirmBody(pending)}
      </ConfirmDialog>
    </div>
  );
}
