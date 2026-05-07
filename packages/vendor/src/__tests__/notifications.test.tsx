import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { VendorLayout } from '@/components/vendor-layout'
import { useUnreadCount, useNotifications, useMarkNotificationRead, useMarkAllRead } from '@/lib/hooks/use-notifications'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  usePathname: () => '/dashboard',
}))
jest.mock('next/link', () => {
  const Link = ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a>
  Link.displayName = 'Link'
  return Link
})
jest.mock('@/lib/auth-store', () => ({
  useAuthStore: jest.fn(() => ({
    isAuthenticated: true,
    vendor: { id: 'vendor-1', businessName: 'Elite Events', status: 'ACTIVE', categories: [] },
    user: { id: 'u1', email: 'v@test.com', firstName: 'Test', lastName: 'Vendor', role: 'vendor' },
    logout: jest.fn(),
  })),
}))
jest.mock('@/lib/hooks/use-sse', () => ({
  useSSE: jest.fn(() => ({ reconnecting: false })),
}))
jest.mock('@/lib/hooks/use-notifications')

const mockUseUnreadCount = useUnreadCount as jest.MockedFunction<typeof useUnreadCount>
const mockUseNotifications = useNotifications as jest.MockedFunction<typeof useNotifications>
const mockUseMarkNotificationRead = useMarkNotificationRead as jest.MockedFunction<typeof useMarkNotificationRead>
const mockUseMarkAllRead = useMarkAllRead as jest.MockedFunction<typeof useMarkAllRead>

const mockNotifications = [
  { id: 'n1', user_id: 'u1', title: 'New Booking', message: 'You have a new booking from Alice', is_read: false, created_at: '2025-07-10T09:00:00Z' },
  { id: 'n2', user_id: 'u1', title: 'Booking Confirmed', message: 'Your booking has been confirmed', is_read: true, created_at: '2025-07-09T14:00:00Z' },
]

function makeClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } })
}

function renderLayout() {
  return render(
    <QueryClientProvider client={makeClient()}>
      <VendorLayout><div>Page content</div></VendorLayout>
    </QueryClientProvider>
  )
}

beforeEach(() => {
  mockUseMarkNotificationRead.mockReturnValue({ mutate: jest.fn(), isPending: false } as ReturnType<typeof useMarkNotificationRead>)
  mockUseMarkAllRead.mockReturnValue({ mutate: jest.fn(), isPending: false } as ReturnType<typeof useMarkAllRead>)
})

describe('Notifications', () => {
  it('renders unread count badge when count > 0', async () => {
    mockUseUnreadCount.mockReturnValue({ data: 3 } as ReturnType<typeof useUnreadCount>)
    mockUseNotifications.mockReturnValue({ data: mockNotifications } as ReturnType<typeof useNotifications>)
    renderLayout()
    await waitFor(() => expect(screen.getByText('3')).toBeInTheDocument())
  })

  it('does not show badge when count is 0', async () => {
    mockUseUnreadCount.mockReturnValue({ data: 0 } as ReturnType<typeof useUnreadCount>)
    mockUseNotifications.mockReturnValue({ data: [] } as ReturnType<typeof useNotifications>)
    renderLayout()
    await waitFor(() => expect(screen.getByLabelText('Notifications')).toBeInTheDocument())
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })

  it('opens notification dropdown when bell is clicked', async () => {
    mockUseUnreadCount.mockReturnValue({ data: 2 } as ReturnType<typeof useUnreadCount>)
    mockUseNotifications.mockReturnValue({ data: mockNotifications } as ReturnType<typeof useNotifications>)
    renderLayout()
    await waitFor(() => expect(screen.getByLabelText('Notifications')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Notifications'))
    await waitFor(() => expect(screen.getByText('You have a new booking from Alice')).toBeInTheDocument())
  })

  it('shows Mark all as read button when there are unread notifications', async () => {
    mockUseUnreadCount.mockReturnValue({ data: 1 } as ReturnType<typeof useUnreadCount>)
    mockUseNotifications.mockReturnValue({ data: mockNotifications } as ReturnType<typeof useNotifications>)
    renderLayout()
    await waitFor(() => expect(screen.getByLabelText('Notifications')).toBeInTheDocument())
    fireEvent.click(screen.getByLabelText('Notifications'))
    await waitFor(() => expect(screen.getByText('Mark all as read')).toBeInTheDocument())
  })
})
