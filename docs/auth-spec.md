# Auth specification

## Roles

| Role | Access |
|---|---|
| `customer` | Chat, portal, own tickets |
| `admin` | All of the above + Admin Dashboard, stats, decisions |

Registration always creates `customer`. Demo `admin` is seeded, not self-serve.

## Register

- Username normalized to lowercase; regex `^[a-zA-Z0-9_.-]{3,32}$`
- Email normalized to lowercase; uniqueness enforced (query + unique sparse index)
- Display name defaults to username
- Password min length 6

## Login

- Identifier is **username** (lowercased)
- Email is stored but not an alternate login id

## Password hashing

- Algorithm: PBKDF2-HMAC-SHA256, 120000 iterations
- Format: `{hex_salt}${hex_digest}`
- Salt: 16 random bytes hex-encoded per user
- Verification: `hmac.compare_digest` against re-derived hash
- Legacy: hashes without `$` compared using JWT secret as salt — do not create new hashes this way

**Do not** derive password hashes from `JWT_SECRET`. Rotating the JWT secret must not invalidate passwords.

## JWT

- Algorithm: HS256, secret `JWT_SECRET`
- Expiry: `JWT_EXPIRE_MINUTES` (default 480)
- Claims:

| Claim | Value |
|---|---|
| `sub` | username |
| `username` | username |
| `email` | stored email or null |
| `role` | `admin` \| `customer` |
| `name` | display name |
| `exp` | expiry |

Bearer scheme via FastAPI `HTTPBearer`. Invalid/missing token → 401. Admin routes require `role == admin` → else 403.

## Demo users

Seeded on bootstrap if username/email not found:

| Username | Email (stored) | Password | Role |
|---|---|---|---|
| `admin` | `admin@example.com` | `admin123` | admin |
| `customer` | `customer@example.com` | `customer123` | customer |

If a row already exists, seed updates `username` and `role` only (does not reset password).

## Client session

SPA stores JWT and user JSON in `localStorage` (`css_token`, `css_user`). Sign-out clears both.
