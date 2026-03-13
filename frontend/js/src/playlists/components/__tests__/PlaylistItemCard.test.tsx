import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import PlaylistItemCard from '../PlaylistItemCard';

// 1. Create a "dummy" track so the component has data to render
const mockTrack = {
  title: "Bohemian Rhapsody",
  creator: "Queen",
  id: "fake-mbid-123",
} as any; 

// 2. Create a fresh Data Engine (QueryClient) for our test environment
const queryClient = new QueryClient();

describe('PlaylistItemCard Component', () => {

  it('renders the drag handle when canEdit is true', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <PlaylistItemCard track={mockTrack} canEdit={true} />
      </QueryClientProvider>
    );

    const dragHandle = screen.getByTitle('Drag to reorder');
    expect(dragHandle).toBeInTheDocument();
  });

  it('does NOT render the drag handle when canEdit is false', () => {
    render(
      <QueryClientProvider client={queryClient}>
        <PlaylistItemCard track={mockTrack} canEdit={false} />
      </QueryClientProvider>
    );

    const dragHandle = screen.queryByTitle('Drag to reorder');
    expect(dragHandle).not.toBeInTheDocument();
  });

});