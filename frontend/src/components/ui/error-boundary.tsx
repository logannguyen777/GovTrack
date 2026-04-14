"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="flex min-h-[300px] items-center justify-center">
          <div className="text-center">
            <AlertTriangle className="mx-auto h-10 w-10 text-[var(--accent-error)]" />
            <h3 className="mt-3 text-lg font-semibold">Đã xảy ra lỗi</h3>
            <p className="mt-1 text-sm text-[var(--text-muted)]">
              {this.state.error?.message || "Lỗi không xác định"}
            </p>
            <button
              onClick={() => this.setState({ hasError: false, error: null })}
              className="mt-4 inline-flex items-center gap-2 rounded-md bg-[var(--accent-primary)] px-4 py-2 text-sm font-medium text-white transition-opacity hover:opacity-90"
            >
              <RefreshCw className="h-4 w-4" />
              Thử lại
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
