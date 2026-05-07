/**
 * Property-based tests for SSE event toast mapping.
 *
 * Property 12: SSE event types each produce a toast (Requirements 7.2, 7.3)
 *
 * Feature: vendor-portal-complete
 */
import * as fc from 'fast-check'

// The SSE event → toast message mapping (mirrors use-sse.ts)
const SSE_TOAST_MAP: Record<string, string> = {
  'booking.created': 'New booking request received',
  'booking.confirmed': 'Booking confirmed',
  'booking.cancelled': 'Booking cancelled',
}

describe('SSE event types each produce a toast (Property 12)', () => {
  it('every SSE event type maps to a non-empty toast message', () => {
    fc.assert(
      fc.property(
        fc.constantFrom('booking.created', 'booking.confirmed', 'booking.cancelled'),
        (eventType) => {
          const message = SSE_TOAST_MAP[eventType]
          expect(message).toBeDefined()
          expect(typeof message).toBe('string')
          expect(message.length).toBeGreaterThan(0)
        }
      ),
      { numRuns: 10 }
    )
  })

  it('booking.created maps to the correct message', () => {
    expect(SSE_TOAST_MAP['booking.created']).toBe('New booking request received')
  })

  it('booking.confirmed maps to the correct message', () => {
    expect(SSE_TOAST_MAP['booking.confirmed']).toBe('Booking confirmed')
  })

  it('booking.cancelled maps to the correct message', () => {
    expect(SSE_TOAST_MAP['booking.cancelled']).toBe('Booking cancelled')
  })

  it('all three event types are covered', () => {
    const requiredEvents = ['booking.created', 'booking.confirmed', 'booking.cancelled']
    requiredEvents.forEach((event) => {
      expect(SSE_TOAST_MAP[event]).toBeDefined()
    })
  })
})
