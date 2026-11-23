import { Component } from 'react';
import ErrorCard from './ErrorCard';

export default class ErrorBoundary extends Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    this.props.onError?.(error, info);
  }

  componentDidUpdate(prevProps) {
    if (this.state.error && prevProps.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <ErrorCard
        message="Something went wrong while showing this page."
        retryLabel="Reload"
        onRetry={() => window.location.reload()}
      />
    );
  }
}
