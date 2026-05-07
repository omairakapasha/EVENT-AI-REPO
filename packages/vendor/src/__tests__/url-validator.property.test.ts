/**
 * Property-based tests for URL validation.
 *
 * Property 11: URL validation rejects non-http(s) strings (Requirements 6.5)
 *
 * Feature: vendor-portal-complete
 */
import * as fc from 'fast-check'
import { z } from 'zod'

// The URL validator used in the profile form (matches the Zod schema in profile/page.tsx)
const urlValidator = z
  .string()
  .optional()
  .refine(
    (val) => !val || val.startsWith('http://') || val.startsWith('https://'),
    { message: 'Website must start with http:// or https://' }
  )

describe('URL validation rejects non-http(s) strings (Property 11)', () => {
  it('rejects any non-empty string not starting with http:// or https://', () => {
    fc.assert(
      fc.property(
        fc
          .string({ minLength: 1 })
          .filter((s) => !s.startsWith('http://') && !s.startsWith('https://')),
        (invalidUrl) => {
          const result = urlValidator.safeParse(invalidUrl)
          expect(result.success).toBe(false)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('accepts strings starting with http://', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).map((s) => `http://${s}`),
        (validUrl) => {
          const result = urlValidator.safeParse(validUrl)
          expect(result.success).toBe(true)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('accepts strings starting with https://', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }).map((s) => `https://${s}`),
        (validUrl) => {
          const result = urlValidator.safeParse(validUrl)
          expect(result.success).toBe(true)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('accepts undefined (website is optional)', () => {
    const result = urlValidator.safeParse(undefined)
    expect(result.success).toBe(true)
  })
})
