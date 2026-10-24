import React from 'react';
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import CopilotMarkdown from '../components/CopilotMarkdown';

describe('CopilotMarkdown', () => {
  it('renders headings, emphasis, lists, and GFM tables with professional structure', () => {
    render(
      <CopilotMarkdown>{`# Inspection rationale

The **support angle** needs *careful inspection*.

1. Inspect the fasteners
2. Record the crack length

- Compare both sides
- Photograph the area

| Check | Result |
| --- | --- |
| Angle | Pending |`}</CopilotMarkdown>
    );

    expect(screen.getByRole('heading', { name: 'Inspection rationale' })).toBeDefined();
    expect(screen.getByText('support angle').tagName).toBe('STRONG');
    expect(screen.getByText('careful inspection').tagName).toBe('EM');
    expect(screen.getByText('Inspect the fasteners').closest('ol')).not.toBeNull();
    expect(screen.getByText('Compare both sides').closest('ul')).not.toBeNull();
    expect(screen.getByRole('table')).toBeDefined();
    expect(screen.getByRole('columnheader', { name: 'Check' })).toBeDefined();
  });

  it('preserves unverified markers in text, lists, tables, and emphasized content', () => {
    render(
      <CopilotMarkdown>{`Text [UNVERIFIED:TEXT-ID].

- List [UNVERIFIED:LIST-ID]

| Source |
| --- |
| [UNVERIFIED:TABLE-ID] |

**[UNVERIFIED:EMPHASIS-ID]**`}</CopilotMarkdown>
    );

    const warnings = document.querySelectorAll('mark[data-unverified="true"]');
    expect(warnings).toHaveLength(4);
    expect(screen.getByText('[UNVERIFIED:TEXT-ID]')).toBeDefined();
    expect(screen.getByText('[UNVERIFIED:LIST-ID]')).toBeDefined();
    expect(screen.getByText('[UNVERIFIED:TABLE-ID]')).toBeDefined();
    expect(screen.getByText('[UNVERIFIED:EMPHASIS-ID]')).toBeDefined();
    warnings.forEach(warning => {
      expect(warning).toHaveAttribute('title', 'Not verified against current evidence');
      expect(within(warning).getByText('Not verified against current evidence')).toBeDefined();
    });
  });

  it('wraps long IDs and keeps wide tables in a keyboard-scrollable container', () => {
    const longId = `SWIA${'1234567890'.repeat(12)}`;
    render(
      <CopilotMarkdown>{`Use \`${longId}\`.

| Record identifier | Finding |
| --- | --- |
| ${longId} | Inspect |`}</CopilotMarkdown>
    );

    expect(screen.getAllByText(longId)).toHaveLength(2);
    expect(screen.getAllByText(longId)[0]).toHaveClass('break-all');
    const table = screen.getByRole('table');
    const scroller = table.parentElement;
    expect(scroller).toHaveClass('overflow-x-auto');
    expect(scroller).toHaveAttribute('tabindex', '0');
    expect(scroller).toHaveAttribute('aria-label', 'Scrollable explanation table');
  });

  it('does not execute raw HTML, unsafe links, or remote images', () => {
    render(
      <CopilotMarkdown>{`<script>window.haliteCompromised = true</script>

<img src="https://attacker.example/raw.png" onerror="alert(1)">

[Unsafe](javascript:alert('xss'))

[Safe reference](https://example.com/reference)

![tracking pixel](https://attacker.example/pixel.png)`}</CopilotMarkdown>
    );

    expect(document.querySelector('script')).toBeNull();
    expect(document.querySelector('img')).toBeNull();
    expect(screen.queryByRole('link', { name: 'Unsafe' })).toBeNull();
    const safeLink = screen.getByRole('link', { name: 'Safe reference' });
    expect(safeLink).toHaveAttribute('href', 'https://example.com/reference');
    expect(safeLink).toHaveAttribute('rel', 'noopener noreferrer');
    expect(screen.getByRole('note')).toHaveTextContent('Remote image not displayed: tracking pixel');
    expect(window.haliteCompromised).toBeUndefined();
  });
});
