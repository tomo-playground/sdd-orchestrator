import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LoadingSpinner from '../ui/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('renders correctly', () => {
    render(<LoadingSpinner />);
    const spinner = screen.getByRole('status');
    expect(spinner).toBeInTheDocument();
    expect(spinner).toHaveClass('animate-spin');
  });

  it('applies size classes correctly', () => {
    render(<LoadingSpinner size="lg" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('h-10 w-10 border-3');
  });

  it('applies custom class names', () => {
    render(<LoadingSpinner className="custom-class" />);
    const spinner = screen.getByRole('status');
    expect(spinner).toHaveClass('custom-class');
  });
});
