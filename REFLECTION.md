# Module 12 Reflection

I connected the existing user and calculation models to HTTP endpoints for
registration, login, and persistent calculation BREAD. The endpoints use the
required `/users/...` URLs and Pydantic schemas. Calculations retain the existing
two-operand design, with results computed on demand.

One challenge was making JWT authentication work with both the database and the
interactive API documentation. Login verifies bcrypt password hashes and returns
the existing access-token response. The bearer dependency looks up the actual user
record, so deleted users and inactive users cannot access calculations. Every
calculation query includes the authenticated user's ID. Create and update requests
also check the supplied `user_id` to prevent assigning calculations to another user.

Boundary checks exposed two validation gaps: bcrypt ignored password bytes after
the first 72, and the email schema allowed values longer than the database column.
Registration and login now enforce the 72-byte UTF-8 password limit, and email
validation matches the 120-character column. Regression tests cover ASCII and
multibyte passwords, an extra password suffix, and email lengths around the limit.

The complete local run passed all 230 tests, including 88 API route tests and the
slow integration tests, with 98% coverage for the `app` package. The Docker image
also passed startup, registration, login, calculation BREAD, and original arithmetic
checks without the source directory mounted into the container.
Browser checks through the built-in Swagger UI verified registration, login,
bearer authorization, and every BREAD operation.

Local Docker verification also exposed a test-environment issue: the pinned older
Playwright version could not install its fallback font packages on the current
Debian image. The temporary verification container used the available Debian
browser libraries instead. Application dependencies and the existing security
pins were preserved.

The existing GitHub Actions pipeline still runs tests, builds and scans the
image, then publishes to Docker Hub after a successful push to `main`. It now
tests pushes on every branch while keeping publication limited to pushes to
`main`.
