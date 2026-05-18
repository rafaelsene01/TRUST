# Architecture — Mock Project

## Overview

This is a mock NestJS + PostgreSQL API used for TRUST E2E testing.

## Modules

- **auth** — handles authentication and session management
- **users** — user CRUD operations
- **payments** — payment processing

## Boundaries

Each module owns its database tables. Cross-module access is only via service interfaces, never direct DB queries across modules.
