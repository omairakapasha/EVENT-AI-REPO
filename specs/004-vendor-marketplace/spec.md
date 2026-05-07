# Feature Specification: Vendor Marketplace

**Feature Branch**: `004-vendor-marketplace`  
**Created**: 2026-04-07  
**Status**: Draft  
**Input**: User description: "Vendor Marketplace    CRUD for vendors, categories, search, approval workflow"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Vendor Self-Registration and Profile Management (Priority: P1)

As a vendor (business/service provider), I want to create and manage my vendor profile through a self-service portal, so that I can showcase my services to potential customers without requiring administrative assistance for basic updates.

**Why this priority**: This is the foundational user journey for vendors—the primary content creators in the marketplace. Without vendor registration and profile management, there are no vendors to display to customers. This enables the marketplace to populate organically.

**Independent Test**: Can be fully tested by a vendor signing up, creating a complete profile with services, contact info, and portfolio, then editing those details later. The vendor can access and modify their own data without admin intervention.

**Acceptance Scenarios**:

1. **Given** I am a new vendor, **When** I register an account and create my vendor profile, **Then** my profile is saved and visible in the marketplace (pending approval if required).

2. **Given** I have an existing vendor profile, **When** I update my contact information, service offerings, or portfolio, **Then** my changes are saved and reflected in my public profile immediately (or after re-approval if content changed significantly).

3. **Given** I am logged in as a vendor, **When** I delete my profile, **Then** my profile is removed from the marketplace and my account is deactivated (with data retention for audit as required).

4. **Given** I attempt to create a profile with invalid data (e.g., malformed email, missing required fields), **When** I submit, **Then** I receive clear error messages indicating what needs correction.

---

### User Story 2 - Category Management and Curation (Priority: P2)

As an administrator, I want to define and manage vendor categories, so that I can organize the marketplace structure and ensure consistent classification for search and filtering.

**Why this priority**: Categories provide essential structure for browsing and searching. Vendors cannot be properly categorized without predefined categories. Admin-controlled ensures consistency. This enables Story 3 (search) but is lower priority than vendor registration itself.

**Independent Test**: Can be tested by an admin creating, editing, and deactivating categories, and assigning vendors to those categories. Changes propagate to vendor profiles and search filters appropriately.

**Acceptance Scenarios**:

1. **Given** I am an admin, **When** I create a new category (e.g., "Wedding Photographers") with description and icon, **Then** the category becomes available for vendors to select during profile creation/editing.

2. **Given** a category exists, **When** I edit its name or description, **Then** all vendors assigned to that category are updated with the new information.

3. **Given** a category has vendors assigned, **When** I attempt to delete it, **Then** the system prevents deletion or requires reassignment of vendors to another category (no orphaned vendors).

4. **Given** categories are defined, **When** a vendor creates/edits their profile, **Then** they can select from the active categories in a dropdown or multi-select interface.

---

### User Story 3 - Vendor Search and Discovery (Priority: P2)

As a customer (event planner or user), I want to search and filter vendors by category, location, and other criteria, so that I can find suitable vendors for my event needs efficiently.

**Why this priority**: Customers need to discover vendors. This is core marketplace functionality but depends on vendors existing and being categorized. Equally important as category management (P2).

**Independent Test**: Can be tested by searching with various keywords, applying category filters, location filters, and sorting results. Search returns relevant vendors with pagination.

**Acceptance Scenarios**:

1. **Given** I am browsing the marketplace, **When** I enter a search query (e.g., "caterer in Karachi"), **Then** I see a list of matching vendors with basic info (name, category, rating, location).

2. **Given** I have too many search results, **When** I apply additional filters (category: "Catering", city: "Karachi", availability: next month), **Then** the results narrow to match all criteria.

3. **Given** I am viewing search results, **When** I sort by rating or price, **Then** the results re-order accordingly.

4. **Given** I perform a search with no matches, **When** I submit, **Then** I receive a helpful message suggesting broader search terms or alternative categories.

5. **Given** I am on a mobile device, **When** I use search and filters, **Then** the interface is responsive and usable.

---

### User Story 4 - Vendor Approval Workflow (Priority: P3)

As an administrator, I want to review and approve vendor registrations and significant profile changes, so that I can maintain marketplace quality and prevent fraudulent or inappropriate listings.

**Why this priority**: Quality control is important for marketplace trust, but can be implemented after basic CRUD is working. Initially vendors might post directly (no approval) for faster growth, then add approval later. Lower priority because it's a moderation layer on top of core CRUD.

**Independent Test**: Can be tested by submitting a new vendor registration or significant profile edit (e.g., adding a new service category), then admin reviewing the submission, approving or rejecting with notes. Vendor receives notification and profile status updates accordingly.

**Acceptance Scenarios**:

1. **Given** a new vendor registers, **When** I (admin) review their submission in the approval queue, **Then** I can approve (profile goes live), reject (vendor receives reason and can revise), or request more information.

2. **Given** an existing vendor makes significant changes (e.g., changes primary category, business name), **When** the change is submitted, **Then** it enters approval queue before going public.

3. **Given** a vendor is rejected, **When** they receive feedback, **Then** they can revise and resubmit for approval.

4. **Given** the approval queue has pending items, **When** an admin processes them, **Then** each decision is logged with timestamp and admin identity for audit.

---

### Edge Cases

- What happens when a vendor attempts to register with an email that already exists? The system should detect duplicate and offer login or password reset instead of creating duplicate profile.

- What happens when a vendor exceeds reasonable profile size limits (too many portfolio images, excessively long description)? The system should enforce limits (e.g., 10 images max, 2000 character description) and provide clear errors.

- What happens when two vendors try to claim the same business name? The system should allow unique business names (or require distinguishing modifiers) and check for conflicts during registration.

- What happens when an admin deactivates a category that has active vendors? Vendors remain assigned to the category (historical) but category is hidden from new assignments; vendors may need to select a new category.

- What happens when search queries are malicious (SQL injection attempts, extremely long strings)? The system must sanitize all inputs, enforce query length limits (e.g., 200 characters), and use parameterized queries to prevent injection.

- What happens during high load (many vendors submitting profiles simultaneously)? The system should handle concurrent registrations without data corruption, using unique constraints and optimistic concurrency control.

- What happens when a vendor tries to delete their profile but has pending bookings or outstanding obligations? The system might prevent deletion or require confirming cancellation of upcoming bookings first; at minimum, retain minimal record for legal compliance.

- What happens when search relevance is poor (users can't find vendors)? The system should include a feedback mechanism ("Did you find what you were looking for?") and allow admin to tweak search weighting or add vendor tags.

- What happens when a vendor's approval is pending for an extended period? The system should send reminder notifications to admins and communicate expected SLA to vendors (e.g., "approval within 48 hours").

- What happens if an admin makes a mistake in approval (approves fraudulent vendor)? The system should allow revoking approval and banning vendors, with audit trail of actions.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST allow vendors to self-register an account and create a vendor profile with business name, contact information, description, service type(s), location, and portfolio.

- **FR-002**: The system MUST allow vendors to view, edit, and update their own profile information, with changes tracked for audit (timestamp, vendor ID, fields modified).

- **FR-003**: The system MUST support soft deletion of vendor profiles (deactivated but retained for audit) and hard deletion (complete removal) with appropriate authorization and confirmation.

- **FR-004**: The system MUST enforce data validation on all vendor profile fields: required fields, email format, phone format, URL validation for website/portfolio, length limits, and acceptable content (no profanity, no prohibited content).

- **FR-005**: The system MUST allow administrators to create, read, update, and deactivate vendor categories (not delete if in use), with each category having a name, description, icon/image, and display order.

- **FR-006**: The system MUST associate vendors with one or more categories selected from active categories, and allow filtering/searching by category.

- **FR-007**: The system MUST provide a search functionality that accepts keyword queries and returns ranked matching vendors based on relevance factors (name, description, category, location).

- **FR-008**: The system MUST support filtering search results by multiple criteria simultaneously: category, geographic location (city/region), service radius, availability, rating, and price range.

- **FR-009**: The system MUST implement pagination for search results with reasonable page size (e.g., 20 per page) and provide total count for pagination controls.

- **FR-010**: The system MUST allow customers to view public vendor profile pages with complete information (name, description, services, portfolio, contact form or booking link).

- **FR-011**: The system MUST implement an approval workflow where new vendor registrations and certain profile edits (e.g., primary category change, business name change) require admin review before becoming publicly visible.

- **FR-012**: The system MUST provide an admin approval queue listing pending vendor submissions with key details and actions: approve, reject with reason, request more information.

- **FR-013**: The system MUST notify vendors via email (or in-app notification) of approval decisions, rejection reasons, or requests for changes.

- **FR-014**: The system MUST log all admin actions (approvals, rejections, category changes, vendor modifications) with user ID, timestamp, and before/after values for audit compliance.

- **FR-015**: The system MUST enforce authorization: vendors can only modify their own profiles; admins have full access; customers have read-only access to public profiles.

- **FR-016**: The system MUST rate-limit sensitive operations (registration, profile updates, search queries) to prevent abuse (e.g., 10 profile updates per hour, 100 searches per hour per user).

- **FR-017**: The system MUST prevent duplicate vendor accounts from the same email or business entity (use unique email and optional business tax ID/registration number for deduplication).

- **FR-018**: The system MUST support uploading and managing portfolio images (multiple per vendor) with size limits, format restrictions (JPG/PNG), and optional CDN storage.

- **FR-019**: The system MUST allow vendors to set their service area (geographic regions served) and availability calendar or general availability status.

- **FR-020**: The system MUST provide a customer inquiry or booking initiation mechanism (contact form or "request quote" button) on vendor profiles.

### Key Entities

- **Vendor**: Represents a business or service provider in the marketplace. Attributes include: unique identifier, user account linkage (auth), business name, business email, business phone, website, description (text), service locations (city/region/radius), service categories (many-to-many with Category), portfolio (collection of images/media), status (pending, active, suspended, rejected), created date, updated date, approval status (bool + approver + timestamp). Vendor may have additional metadata like rating (derived from reviews), response time.

- **Category**: Represents a vendor classification or service type. Attributes include: unique identifier, category name (unique), description, icon/image URL, display order (integer for sorting), active status (bool), created date, updated date. Categories are curated by admin; multiple categories allowed per vendor (many-to-many).

- **VendorProfileVersion** (optional but recommended for audit): Represents historical versions of vendor profile changes. Attributes include: profile version ID, vendor ID (foreign key), snapshot of profile data at that time, change reason (user edit, admin edit, approval), changed by (user ID or admin ID), timestamp. Used for audit and rollback.

- **ApprovalRequest**: Represents a pending approval item for admin review. Attributes include: unique identifier, vendor ID (or vendor profile version ID), request type (new_registration, profile_edit_approval), current status (pending, approved, rejected, more_info), submitted date, reviewed date, reviewed by (admin ID), decision notes, associated data snapshot. One approval request per significant event requiring approval.

- **CustomerInquiry** or **BookingRequest**: Represents a customer reaching out to a vendor. Attributes include: inquiry ID, vendor ID (foreign key), customer contact info (name, email, phone), message content, preferred service date/time, status (new, contacted, quoted, converted, declined), timestamps. Used for tracking leads and conversion.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Vendors can complete profile creation (including uploading up to 5 portfolio images) in under 10 minutes on average (measured from registration start to submission).

- **SC-002**: Search queries return relevant results (top 10 results contain at least one relevant vendor for 90% of queries) in under 500 milliseconds.

- **SC-003**: 95% of vendor registrations are either approved or rejected within 48 hours of submission (admin response time SLA).

- **SC-004**: System supports at least 1,000 active vendor profiles without degradation in search or profile management performance.

- **SC-005**: 90% of customers who perform a search contact at least one vendor (measured via click-through to inquiry/booking).

- **SC-006**: Duplicate vendor registrations are automatically detected and prevented with ≥99% accuracy (same email or same business name + location).

- **SC-007**: The system maintains zero unauthorized profile modifications (audit log shows no unmatched write operations).

### User Satisfaction

- Vendors rate profile creation experience ≥4/5 for ease of use and clarity.
- Admins rate approval workflow efficiency ≥4/5 (queue management, decision speed).
- Customers rate search satisfaction ≥4/5 (relevance, speed, usability).

### Business Impact

- Grow vendor base to 500+ active vendors within 6 months of launch.
- Increase customer inquiry conversion rate to ≥30% (inquiries become bookings).
- Reduce time spent by admins on manual vendor onboarding from 30 minutes per vendor to <5 minutes (automation + efficient approval queue).
- Maintain marketplace quality score (measured by customer satisfaction surveys) ≥4/5.

## Assumptions

- Vendors are authenticated users (user registration/login system exists from `002-user-auth`). Vendor profiles are linked to user accounts. The spec focuses on vendor-specific data and workflows; authentication is out of scope handled by prior feature.

- Categories are managed by administrators (staff users with elevated permissions); vendor self-service cannot create new categories—only select from existing ones.

- Approval workflow uses a single-tier admin review. Multi-tier approval or vendor-paid verification tiers are out of scope for this version.

- Search implementation uses full-text search capabilities of PostgreSQL (e.g., Trigram indexes, full-text search on name/description). External search services (Algolia, Elastic) are not in scope for MVP but can be added later.

- Portfolio images are uploaded to a CDN or object storage (e.g., AWS S3, Cloudflare R2); the system stores URLs. Image resizing and optimization are handled separately (not in this spec).

- Customer inquiries trigger email notifications to vendors and optionally to customers; the actual email delivery infrastructure exists or will be implemented in a separate notification feature.

- Geographic location filtering uses city/region fields (text) and optionally coordinates for proximity search. Full geospatial queries with radius may use PostGIS if needed; pgvector is not used for search (vector search for semantic matching is separate and not required).

- The marketplace is a Next.js frontend portal (`packages/vendor` per constitution) that consumes REST API endpoints from Backend package. This spec defines only the backend API and data model; frontend UI implementation is separate.

- Vendor profile data model includes fields for business name, description, contact, services, location, portfolio. Additional fields (insurance, licenses, certifications) may be added later; this is the MVP set.

- Approval workflow: new registrations require approval before profile becomes public. Edits to non-critical fields (description, portfolio images) may be auto-approved; edits to critical fields (business name, primary category) require re-approval. The spec expects configurable rules.

- The system enforces constitutional security standards: rate limiting, input validation, authorization checks, audit logging. JWT tokens from auth feature protect all vendor-facing endpoints.

- Database is the cloud-only Neon PostgreSQL from `003-database-setup`. Vendor and Category tables reside in `public` schema managed by Backend package (Prisma). ApprovalRequest and CustomerInquiry also in `public`.

- Vendor search performance is optimized with database indexes: on category foreign keys, location fields, full-text indexes on name/description, and possibly trigram indexes for fuzzy matching.

- Content moderation (profanity, prohibited content) uses automated pre-screening (word filters) plus human admin review. Infrastructure is part of this spec.
