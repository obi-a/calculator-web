# Module 11 Reflection

I added a calculation model, validation schemas, and a factory that reuses
the existing arithmetic functions. Each calculation stores two numbers, its type,
and its owner's ID. The result is calculated when needed. Existing calculator and
user features stayed the same.

The calculation and user models share the same SQLAlchemy base so the foreign key
works correctly. Validation rejects invalid inputs and division by zero.
PostgreSQL tests check that calculations are saved correctly and reference valid
user records.

I also fixed the Docker health check to use the existing home page. GitHub Actions
built the image, but the security scan found a vulnerable dnspython dependency.
I updated it to version 2.9.2 to address that finding.

The full local test run passed all 138 tests with 98% application coverage.
After the dependency update, GitHub Actions passed all 138 tests, built the image,
passed the security scan, and published the image to Docker Hub.
