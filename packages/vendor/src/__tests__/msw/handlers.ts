import { http, HttpResponse } from 'msw'

const BASE_URL = 'http://localhost:5000/api/v1'

// Mock data
const mockDashboardStats = {
  total_bookings: 42,
  pending_bookings: 5,
  confirmed_bookings: 12,
  active_services: 8,
  total_services: 10,
  recent_bookings: [
    {
      id: 'booking-1',
      service_name: 'Photography Package',
      event_date: '2025-08-15',
      status: 'confirmed',
      total_price: 500.0,
      currency: 'USD',
      client_name: 'Alice Johnson',
    },
    {
      id: 'booking-2',
      service_name: 'Catering Service',
      event_date: '2025-08-10',
      status: 'pending',
      total_price: 1200.0,
      currency: 'USD',
      client_name: 'Bob Smith',
    },
    {
      id: 'booking-3',
      service_name: 'DJ Service',
      event_date: '2025-08-05',
      status: 'completed',
      total_price: 800.0,
      currency: 'USD',
      client_name: 'Carol White',
    },
    {
      id: 'booking-4',
      service_name: 'Decoration',
      event_date: '2025-07-30',
      status: 'cancelled',
      total_price: 300.0,
      currency: 'USD',
      client_name: 'David Brown',
    },
    {
      id: 'booking-5',
      service_name: 'Venue Setup',
      event_date: '2025-07-25',
      status: 'in_progress',
      total_price: 650.0,
      currency: 'USD',
      client_name: 'Eve Davis',
    },
  ],
}

const mockBookings = [
  {
    id: 'booking-1',
    user_id: 'user-1',
    vendor_id: 'vendor-1',
    service_id: 'service-1',
    service_name: 'Photography Package',
    event_date: '2025-08-15',
    status: 'confirmed',
    payment_status: 'paid',
    unit_price: 500.0,
    total_price: 500.0,
    currency: 'USD',
    event_location: { city: 'Karachi', country: 'Pakistan' },
    client_name: 'Alice Johnson',
    created_at: '2025-07-01T10:00:00Z',
    updated_at: '2025-07-01T10:00:00Z',
  },
  {
    id: 'booking-2',
    user_id: 'user-2',
    vendor_id: 'vendor-1',
    service_id: 'service-2',
    service_name: 'Catering Service',
    event_date: '2025-08-10',
    status: 'pending',
    payment_status: 'pending',
    unit_price: 1200.0,
    total_price: 1200.0,
    currency: 'USD',
    event_location: { city: 'Lahore', country: 'Pakistan' },
    client_name: 'Bob Smith',
    created_at: '2025-07-02T10:00:00Z',
    updated_at: '2025-07-02T10:00:00Z',
  },
]

const mockServices = [
  {
    id: 'service-1',
    vendor_id: 'vendor-1',
    name: 'Photography Package',
    description: 'Professional photography for events',
    price_min: 300.0,
    price_max: 800.0,
    capacity: 1,
    is_active: true,
    categories: [{ id: 'cat-1', name: 'Photography', slug: 'photography' }],
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'service-2',
    vendor_id: 'vendor-1',
    name: 'Catering Service',
    description: 'Full catering for events up to 500 guests',
    price_min: 1000.0,
    price_max: 5000.0,
    capacity: 500,
    is_active: true,
    categories: [{ id: 'cat-2', name: 'Catering', slug: 'catering' }],
    created_at: '2025-01-02T00:00:00Z',
    updated_at: '2025-01-02T00:00:00Z',
  },
]

const mockAvailability = [
  {
    id: 'avail-1',
    vendor_id: 'vendor-1',
    service_id: null,
    date: '2025-08-01',
    status: 'available',
    notes: null,
    booking_id: null,
    created_at: '2025-07-01T00:00:00Z',
    updated_at: '2025-07-01T00:00:00Z',
  },
  {
    id: 'avail-2',
    vendor_id: 'vendor-1',
    service_id: null,
    date: '2025-08-02',
    status: 'blocked',
    notes: 'Personal day',
    booking_id: null,
    created_at: '2025-07-01T00:00:00Z',
    updated_at: '2025-07-01T00:00:00Z',
  },
  {
    id: 'avail-3',
    vendor_id: 'vendor-1',
    service_id: null,
    date: '2025-08-03',
    status: 'booked',
    notes: null,
    booking_id: 'booking-1',
    created_at: '2025-07-01T00:00:00Z',
    updated_at: '2025-07-01T00:00:00Z',
  },
]

const mockVendorProfile = {
  id: 'vendor-1',
  user_id: 'user-vendor-1',
  business_name: 'Elite Events Co.',
  description: 'Premium event services in Pakistan',
  contact_email: 'contact@eliteevents.pk',
  contact_phone: '+92-300-1234567',
  website: 'https://eliteevents.pk',
  logo_url: null,
  city: 'Karachi',
  region: 'Sindh',
  status: 'ACTIVE',
  rating: 4.8,
  total_reviews: 127,
  categories: [
    { id: 'cat-1', name: 'Photography', slug: 'photography' },
    { id: 'cat-2', name: 'Catering', slug: 'catering' },
  ],
}

const mockNotifications = [
  {
    id: 'notif-1',
    user_id: 'user-vendor-1',
    title: 'New Booking Request',
    message: 'You have a new booking request from Alice Johnson',
    is_read: false,
    created_at: '2025-07-10T09:00:00Z',
  },
  {
    id: 'notif-2',
    user_id: 'user-vendor-1',
    title: 'Booking Confirmed',
    message: 'Your booking for Photography Package has been confirmed',
    is_read: true,
    created_at: '2025-07-09T14:00:00Z',
  },
  {
    id: 'notif-3',
    user_id: 'user-vendor-1',
    title: 'Payment Received',
    message: 'Payment of $500 received for booking #booking-1',
    is_read: false,
    created_at: '2025-07-08T11:00:00Z',
  },
]

export const handlers = [
  // GET /api/v1/vendors/me/dashboard
  http.get(`${BASE_URL}/vendors/me/dashboard`, () => {
    return HttpResponse.json({
      success: true,
      data: mockDashboardStats,
    })
  }),

  // GET /api/v1/vendors/me/bookings
  http.get(`${BASE_URL}/vendors/me/bookings`, () => {
    return HttpResponse.json({
      success: true,
      data: mockBookings,
      meta: {
        total: mockBookings.length,
        page: 1,
        limit: 20,
        pages: 1,
      },
    })
  }),

  // GET /api/v1/vendors/me/services
  http.get(`${BASE_URL}/vendors/me/services`, () => {
    return HttpResponse.json({
      success: true,
      data: mockServices,
      meta: {
        total: mockServices.length,
        page: 1,
        limit: 20,
        pages: 1,
      },
    })
  }),

  // GET /api/v1/vendors/me/availability
  http.get(`${BASE_URL}/vendors/me/availability`, () => {
    return HttpResponse.json({
      success: true,
      data: mockAvailability,
    })
  }),

  // GET /api/v1/vendors/profile/me
  http.get(`${BASE_URL}/vendors/profile/me`, () => {
    return HttpResponse.json({
      success: true,
      data: mockVendorProfile,
    })
  }),

  // GET /api/v1/notifications/
  http.get(`${BASE_URL}/notifications/`, () => {
    return HttpResponse.json({
      success: true,
      data: mockNotifications,
    })
  }),

  // GET /api/v1/notifications/unread-count
  http.get(`${BASE_URL}/notifications/unread-count`, () => {
    return HttpResponse.json({
      success: true,
      data: { count: 3 },
    })
  }),

  // POST /api/v1/vendors/me/availability
  http.post(`${BASE_URL}/vendors/me/availability`, async ({ request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      success: true,
      data: {
        id: 'avail-new',
        vendor_id: 'vendor-1',
        service_id: body.service_id ?? null,
        date: body.date,
        status: body.status,
        notes: body.notes ?? null,
        booking_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      },
    })
  }),

  // PATCH /api/v1/vendors/me/bookings/:id/status
  http.patch(`${BASE_URL}/vendors/me/bookings/:id/status`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    const booking = mockBookings.find((b) => b.id === params.id) ?? mockBookings[0]
    return HttpResponse.json({
      success: true,
      data: {
        ...booking,
        status: body.status,
        updated_at: new Date().toISOString(),
      },
    })
  }),

  // POST /api/v1/bookings/:id/messages
  http.post(`${BASE_URL}/bookings/:id/messages`, async ({ params, request }) => {
    const body = await request.json() as Record<string, unknown>
    return HttpResponse.json({
      success: true,
      data: {
        id: 'msg-new',
        booking_id: params.id,
        sender_id: 'user-vendor-1',
        sender_role: 'vendor',
        content: body.content,
        created_at: new Date().toISOString(),
      },
    })
  }),
]
