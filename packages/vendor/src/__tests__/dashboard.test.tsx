import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import DashboardPage from '@/app/dashboard/page'
import { useDashboard } from '@/lib/hooks/use-dashboard'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/dashboard',
  useSearchParams: () => ({ get: () => null }),
}))
jest.mock('next/link', () => {
  const Link = ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>
  Link.displayName = 'Link'
  return Link
})
jest.mock('@/lib/auth-store', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    user: { id: 'u1', email: 'v@test.com', firstName: 'Test', lastName: 'Vendor', role: 'vendor' },
    vendor: { id: 'vendor-1', businessName: 'Elite Events Co.', status: 'ACTIVE', categories: [] },
    loginWithTokens: jest.fn(),
  })),
}))
jest.mock('@/components/vendor-layout', () => ({
  VendorLayout: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}))
jest.mock('@/lib/hooks/use-dashboard')

const mockUseDashboard = useDashboard as jest.MockedFunction<typeof useDashboard>

const mockDashboard = {
  total_bookings: 42,
  pending_bookings: 5,
  confirmed_bookings: 12,
  active_services: 8,
  total_services: 10,
  recent_bookings: [
    { id: 'b1', service_name: 'Photography', event_date: '2025-08-15', status: 'confirmed', total_price: 500, currency: 'USD', client_name: 'Alice' },
    { id: 'b2', service_name: 'Catering', event_date: '2025-08-10', status: 'pending', total_price: 1200, currency: 'USD', client_name: 'Bob' },
    { id: 'b3', service_name: 'DJ', event_date: '2025-08-05', status: 'completed', total_price: 800, currency: 'USD', client_name: 'Carol' },
    { id: 'b4', service_name: 'Decoration', event_date: '2025-07-30', status: 'cancelled', total_price: 300, currency: 'USD', client_name: 'Dave' },
    { id: 'b5', service_name: 'Venue', event_date: '2025-07-25', status: 'in_progress', total_price: 650, currency: 'USD', client_name: 'Eve' },
  ],
}

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderDashboard() {
  return render(<QueryClientProvider client={makeClient()}><DashboardPage /></QueryClientProvider>)
}

describe('Dashboard page', () => {
  it('renders stat cards with correct values on success', async () => {
    mockUseDashboard.mockReturnValue({ data: mockDashboard, isLoading: false, isError: false, refetch: jest.fn() } as ReturnType<typeof useDashboard>)
    renderDashboard()
    await waitFor(() => expect(screen.getByText('42')).toBeInTheDocument())
    expect(screen.getByText('5')).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()
  })

  it('renders recent bookings table with service names', async () => {
    mockUseDashboard.mockReturnValue({ data: mockDashboard, isLoading: false, isError: false, refetch: jest.fn() } as ReturnType<typeof useDashboard>)
    renderDashboard()
    await waitFor(() => expect(screen.getByText('Photography')).toBeInTheDocument())
    expect(screen.getByText('Catering')).toBeInTheDocument()
    expect(screen.getByText('DJ')).toBeInTheDocument()
  })

  it('renders error state with retry button when request fails', async () => {
    mockUseDashboard.mockReturnValue({ data: undefined, isLoading: false, isError: true, refetch: jest.fn() } as ReturnType<typeof useDashboard>)
    renderDashboard()
    await waitFor(() => expect(screen.getByText(/failed to load/i)).toBeInTheDocument())
    expect(screen.getByText(/retry/i)).toBeInTheDocument()
  })

  it('renders loading skeletons while fetching', async () => {
    mockUseDashboard.mockReturnValue({ data: undefined, isLoading: true, isError: false, refetch: jest.fn() } as ReturnType<typeof useDashboard>)
    renderDashboard()
    expect(screen.getByText('Recent Bookings')).toBeInTheDocument()
  })

  it('renders the Recent Bookings heading', async () => {
    mockUseDashboard.mockReturnValue({ data: mockDashboard, isLoading: false, isError: false, refetch: jest.fn() } as ReturnType<typeof useDashboard>)
    renderDashboard()
    await waitFor(() => expect(screen.getByText('Recent Bookings')).toBeInTheDocument())
  })
})
