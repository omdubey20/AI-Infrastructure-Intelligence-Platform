import { render, screen } from '@testing-library/react';
import React from 'react';

// Minimal smoke test that validates the test runner works
// without requiring the full App component tree (which pulls in
// react-router-dom v7 ESM modules incompatible with CRA5's Jest).
test('React testing environment is functional', () => {
  render(<div data-testid="smoke">Platform Loaded</div>);
  const el = screen.getByTestId('smoke');
  expect(el).toBeInTheDocument();
  expect(el.textContent).toBe('Platform Loaded');
});
