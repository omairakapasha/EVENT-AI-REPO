/**
 * Property-based tests for API error envelope extraction.
 *
 * Property 13: API error envelope extraction (Requirements 9.2)
 *
 * Feature: vendor-portal-complete
 */
import * as fc from 'fast-check'
import axios from 'axios'
import { getApiError } from '../lib/api'

describe('getApiError envelope extraction (Property 13)', () => {
  it('extracts error.message from backend envelope for any input', () => {
    fc.assert(
      fc.property(
        fc.record({
          code: fc.string({ minLength: 1 }),
          message: fc.string({ minLength: 1 }),
        }),
        ({ code, message }) => {
          const axiosError = new axios.AxiosError(
            'Request failed',
            'ERR_BAD_RESPONSE',
            undefined,
            undefined,
            {
              data: { success: false, error: { code, message } },
              status: 400,
              statusText: 'Bad Request',
              headers: {},
              config: {} as never,
            }
          )
          const result = getApiError(axiosError)
          expect(result).toBe(message)
        }
      ),
      { numRuns: 25 }
    )
  })

  it('returns a non-empty string for any error input', () => {
    fc.assert(
      fc.property(
        fc.record({
          code: fc.string({ minLength: 1 }),
          message: fc.string({ minLength: 1 }),
        }),
        ({ code, message }) => {
          const axiosError = new axios.AxiosError(
            'Request failed',
            'ERR_BAD_RESPONSE',
            undefined,
            undefined,
            {
              data: { success: false, error: { code, message } },
              status: 422,
              statusText: 'Unprocessable Entity',
              headers: {},
              config: {} as never,
            }
          )
          const result = getApiError(axiosError)
          expect(typeof result).toBe('string')
          expect(result.length).toBeGreaterThan(0)
        }
      ),
      { numRuns: 25 }
    )
  })
})
