import { useState } from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { Button, ConfirmDialog, ErrorBoundary, Tabs } from '../components/ui';

const TABS = [
  { id: 'a', label: 'Alpha', content: <p>Alpha panel</p> },
  { id: 'b', label: 'Beta', content: <p>Beta panel</p> },
  { id: 'c', label: 'Gamma', content: <p>Gamma panel</p> },
];

describe('Tabs', () => {
  it('selects the first tab and shows its panel', () => {
    render(<Tabs tabs={TABS} label="Demo" />);
    expect(screen.getByRole('tab', { name: 'Alpha' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Alpha panel');
  });

  it('moves selection with arrow keys, wrapping and Home/End', () => {
    render(<Tabs tabs={TABS} label="Demo" />);
    const alpha = screen.getByRole('tab', { name: 'Alpha' });
    fireEvent.keyDown(alpha, { key: 'ArrowRight' });
    expect(screen.getByRole('tab', { name: 'Beta' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Beta' })).toHaveFocus();
    expect(screen.getByRole('tabpanel')).toHaveTextContent('Beta panel');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Beta' }), { key: 'End' });
    expect(screen.getByRole('tab', { name: 'Gamma' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Gamma' }), { key: 'ArrowRight' });
    expect(screen.getByRole('tab', { name: 'Alpha' })).toHaveAttribute('aria-selected', 'true');
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Alpha' }), { key: 'ArrowLeft' });
    expect(screen.getByRole('tab', { name: 'Gamma' })).toHaveAttribute('aria-selected', 'true');
  });

  it('selects on click and reports the change', () => {
    const onChange = vi.fn();
    render(<Tabs tabs={TABS} onChange={onChange} />);
    fireEvent.click(screen.getByRole('tab', { name: 'Beta' }));
    expect(onChange).toHaveBeenCalledWith('b');
  });
});

describe('ConfirmDialog', () => {
  function setup(props = {}) {
    const onConfirm = vi.fn();
    const onCancel = vi.fn();
    render(
      <ConfirmDialog open title="Delete it?" onConfirm={onConfirm} onCancel={onCancel} {...props}>
        Body
      </ConfirmDialog>,
    );
    return { onConfirm, onCancel };
  }

  it('is a labelled modal dialog', () => {
    setup();
    const dialog = screen.getByRole('dialog', { name: 'Delete it?' });
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('confirms and cancels via buttons', () => {
    const { onConfirm, onCancel } = setup();
    fireEvent.click(screen.getByRole('button', { name: 'Confirm' }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('cancels on Escape', () => {
    const { onCancel } = setup();
    fireEvent.keyDown(screen.getByRole('dialog'), { key: 'Escape' });
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('ignores Escape and backdrop clicks while loading', () => {
    const { onCancel } = setup({ loading: true });
    const dialog = screen.getByRole('dialog');
    fireEvent.keyDown(dialog, { key: 'Escape' });
    fireEvent.mouseDown(dialog.parentElement);
    expect(onCancel).not.toHaveBeenCalled();
  });

  it('cancels on backdrop click but not on dialog click', () => {
    const { onCancel } = setup();
    fireEvent.mouseDown(screen.getByRole('dialog'));
    expect(onCancel).not.toHaveBeenCalled();
    fireEvent.mouseDown(screen.getByRole('dialog').parentElement);
    expect(onCancel).toHaveBeenCalledTimes(1);
  });

  it('moves focus in and returns it on close', () => {
    function Host() {
      const [open, setOpen] = useState(false);
      return (
        <>
          <button onClick={() => setOpen(true)}>Open</button>
          <ConfirmDialog open={open} title="T" onConfirm={() => {}} onCancel={() => setOpen(false)} />
        </>
      );
    }
    render(<Host />);
    const opener = screen.getByRole('button', { name: 'Open' });
    opener.focus();
    fireEvent.click(opener);
    expect(screen.getByRole('button', { name: 'Cancel' })).toHaveFocus();
    fireEvent.click(screen.getByRole('button', { name: 'Cancel' }));
    expect(opener).toHaveFocus();
  });
});

describe('ErrorBoundary', () => {
  function Bomb({ explode }) {
    if (explode) throw new Error('boom');
    return <p>All good</p>;
  }

  it('catches errors, shows the card, and clears when resetKey changes', () => {
    const spy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const { rerender } = render(
      <ErrorBoundary resetKey={1}><Bomb explode /></ErrorBoundary>,
    );
    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reload' })).toBeInTheDocument();
    rerender(<ErrorBoundary resetKey={2}><Bomb explode={false} /></ErrorBoundary>);
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.getByText('All good')).toBeInTheDocument();
    spy.mockRestore();
  });
});

describe('Button', () => {
  it('defaults to type button', () => {
    render(<Button>Go</Button>);
    expect(screen.getByRole('button', { name: 'Go' })).toHaveAttribute('type', 'button');
  });

  it('disables and shows progress while loading', () => {
    const onClick = vi.fn();
    render(<Button loading onClick={onClick}>Save</Button>);
    const button = screen.getByRole('button');
    expect(button).toBeDisabled();
    expect(button).toHaveAttribute('aria-busy', 'true');
    expect(button).toHaveTextContent('Loading');
    fireEvent.click(button);
    expect(onClick).not.toHaveBeenCalled();
  });
});
