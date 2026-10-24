import { Children, Fragment, isValidElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { splitUnverified } from '../utils/diagnostics';

const UNVERIFIED_PATTERN = /\[UNVERIFIED(?::[^\]]*)?\]/;

function renderUnverified(children) {
  return Children.map(children, (child) => {
    if (typeof child !== 'string') return child;

    return splitUnverified(child).map((segment, index) => segment.flagged ? (
      <mark
        key={`${segment.text}-${index}`}
        data-unverified="true"
        title="Not verified against current evidence"
        className="mx-0.5 inline-flex max-w-full flex-wrap items-baseline gap-x-1 rounded border border-amber-500/40 bg-amber-500/10 px-1.5 py-0.5 text-amber-300"
      >
        <span className="break-all font-mono text-[0.78em]">{segment.text}</span>
        <span className="font-sans text-[0.72em] font-medium">Not verified against current evidence</span>
      </mark>
    ) : <Fragment key={`${index}-${segment.text}`}>{segment.text}</Fragment>);
  });
}

function containsUnverified(children) {
  return Children.toArray(children).some((child) => {
    if (typeof child === 'string') return UNVERIFIED_PATTERN.test(child);
    return isValidElement(child) && containsUnverified(child.props.children);
  });
}

function safeMarkdownUrl(url) {
  if (typeof url !== 'string') return '';
  const value = url.trim();
  if (/^https?:\/\//i.test(value)) return value;
  if (/^(?:#|\?|\/(?!\/)|\.\.?\/)/.test(value)) return value;
  return '';
}

const textComponents = {
  h1: ({ children }) => <h3 className="mt-5 font-brand text-xl leading-tight text-primary first:mt-0">{renderUnverified(children)}</h3>,
  h2: ({ children }) => <h4 className="mt-5 font-brand text-lg leading-snug text-primary first:mt-0">{renderUnverified(children)}</h4>,
  h3: ({ children }) => <h5 className="mt-4 font-sans text-base font-semibold text-primary first:mt-0">{renderUnverified(children)}</h5>,
  h4: ({ children }) => <h6 className="mt-4 font-sans text-sm font-semibold uppercase tracking-wide text-primary first:mt-0">{renderUnverified(children)}</h6>,
  h5: ({ children }) => <h6 className="mt-4 font-sans text-sm font-semibold text-primary first:mt-0">{renderUnverified(children)}</h6>,
  h6: ({ children }) => <h6 className="mt-4 font-sans text-sm font-medium text-secondary first:mt-0">{renderUnverified(children)}</h6>,
  p: ({ children }) => <p className="my-3 whitespace-normal break-words font-sans text-sm leading-6 text-primary first:mt-0 last:mb-0">{renderUnverified(children)}</p>,
  strong: ({ children }) => <strong className="font-semibold text-primary">{renderUnverified(children)}</strong>,
  em: ({ children }) => <em className="text-primary">{renderUnverified(children)}</em>,
  ul: ({ children }) => <ul className="my-3 list-disc space-y-1.5 pl-6 font-sans text-sm leading-6 text-primary">{children}</ul>,
  ol: ({ children }) => <ol className="my-3 list-decimal space-y-1.5 pl-6 font-sans text-sm leading-6 text-primary">{children}</ol>,
  li: ({ children }) => <li className="break-words pl-1 marker:text-accent">{renderUnverified(children)}</li>,
  blockquote: ({ children }) => <blockquote className="my-3 border-l-2 border-accent/60 pl-3 text-secondary">{children}</blockquote>,
  hr: () => <hr className="my-5 border-theme" />,
  table: ({ children }) => (
    <div className="my-4 max-w-full overflow-x-auto rounded-lg border border-theme" tabIndex="0" aria-label="Scrollable explanation table">
      <table className="w-full min-w-max border-collapse text-left font-sans text-sm text-primary">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-page/60 text-xs uppercase tracking-wide text-secondary">{children}</thead>,
  tbody: ({ children }) => <tbody className="divide-y divide-theme">{children}</tbody>,
  tr: ({ children }) => <tr className="divide-x divide-theme">{children}</tr>,
  th: ({ children }) => <th className="px-3 py-2 font-semibold text-primary">{renderUnverified(children)}</th>,
  td: ({ children }) => <td className="max-w-md break-words px-3 py-2 align-top">{renderUnverified(children)}</td>,
  pre: ({ children }) => <pre className="my-3 max-w-full overflow-x-auto rounded-lg border border-theme bg-page/70 p-3 font-mono text-xs leading-5 text-primary">{children}</pre>,
  code: ({ children, className }) => (
    <code className={`${className ?? ''} break-all rounded bg-page/70 px-1 py-0.5 font-mono text-[0.9em] text-accent`}>
      {renderUnverified(children)}
    </code>
  ),
  a: ({ children, href }) => {
    const content = renderUnverified(children);
    if (!href || containsUnverified(children)) {
      return <span className="break-all text-primary">{content}</span>;
    }
    const external = /^https?:\/\//i.test(href);
    return (
      <a
        href={href}
        {...(external ? { target: '_blank', rel: 'noopener noreferrer' } : {})}
        className="break-all font-medium text-accent underline decoration-accent/50 underline-offset-2 hover:decoration-accent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
      >
        {content}
      </a>
    );
  },
  img: ({ alt }) => (
    <span role="note" className="font-sans text-xs italic text-secondary">
      [Remote image not displayed{alt ? `: ${alt}` : ''}]
    </span>
  ),
};

export default function CopilotMarkdown({ children }) {
  return (
    <div data-testid="copilot-explanation" className="min-w-0 max-w-none overflow-hidden">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        skipHtml
        urlTransform={safeMarkdownUrl}
        components={textComponents}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
