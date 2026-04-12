# VNeID Integration — Đề án 06

Đề án 06 (QĐ 06/QĐ-TTg/2022) là chương trình quốc gia về định danh điện tử và cơ sở dữ liệu dân cư, với **VNeID** là ứng dụng định danh của Bộ Công an.

## Why VNeID matters for GovFlow

1. **Citizen authentication** — công dân đăng nhập Citizen Portal qua VNeID, không cần tạo tài khoản riêng
2. **Identity verification** — xác thực danh tính cho TTHC (tương đương CMND/CCCD)
3. **Data pre-fill** — VNeID trả về thông tin cá nhân đã được xác thực → auto-fill form
4. **Legal validity** — chữ ký số VNeID có giá trị pháp lý theo NĐ 45/2020
5. **Political alignment** — đây là ưu tiên quốc gia, làm gì cũng cần có hook VNeID

## Integration architecture

```
┌────────────────────────┐
│   Citizen Portal        │
│   (Next.js frontend)    │
└───────────┬────────────┘
            │ "Đăng nhập qua VNeID"
            ▼
┌────────────────────────┐
│   FastAPI backend       │
└───────────┬────────────┘
            │ OAuth 2.0 flow
            ▼
┌────────────────────────┐
│   VNeID OAuth server    │
│   (api.vneid.gov.vn)    │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   Bộ Công an — CSDLQG  │
│   về dân cư            │
└────────────────────────┘
```

## OAuth 2.0 flow

```
Citizen Portal → "Đăng nhập VNeID"
              → redirect to VNeID authorize URL
              → citizen approves on VNeID app
              → redirect back with authorization code
              → backend exchanges code for access token
              → backend fetches user profile
              → create/update Applicant vertex in GDB
              → set JWT session for Citizen Portal
```

### Code sketch

```python
# backend/auth/vneid.py

VNEID_AUTHORIZE_URL = "https://api.vneid.gov.vn/oauth2/authorize"
VNEID_TOKEN_URL = "https://api.vneid.gov.vn/oauth2/token"
VNEID_USERINFO_URL = "https://api.vneid.gov.vn/oauth2/userinfo"

async def initiate_vneid_login():
    """Redirect citizen to VNeID login."""
    state = generate_csrf_state()
    params = {
        'client_id': VNEID_CLIENT_ID,
        'redirect_uri': VNEID_REDIRECT_URI,
        'response_type': 'code',
        'scope': 'profile id_card address',
        'state': state
    }
    return redirect(f"{VNEID_AUTHORIZE_URL}?{urlencode(params)}")

async def vneid_callback(code: str, state: str):
    """Handle VNeID callback."""
    verify_csrf(state)

    # Exchange code for token
    token_response = await httpx.post(VNEID_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': VNEID_CLIENT_ID,
        'client_secret': VNEID_CLIENT_SECRET,
        'redirect_uri': VNEID_REDIRECT_URI
    })
    tokens = token_response.json()

    # Fetch user profile
    profile_response = await httpx.get(
        VNEID_USERINFO_URL,
        headers={'Authorization': f'Bearer {tokens["access_token"]}'}
    )
    profile = profile_response.json()

    # Create/update Applicant in GDB
    applicant_id = await upsert_applicant(profile)

    # Create GovFlow JWT
    govflow_jwt = create_jwt(
        sub=profile['vneid_subject'],
        applicant_id=applicant_id,
        role='citizen',
        clearance_level='Unclassified',  # citizens are always Unclassified for their own cases
        vneid_verified=True
    )

    return {'token': govflow_jwt, 'profile': profile}
```

### User profile from VNeID

```json
{
  "vneid_subject": "VN-XXXXXXXX",
  "national_id": "079200012345",  // CCCD
  "full_name": "Nguyễn Văn Minh",
  "date_of_birth": "1986-03-15",
  "gender": "male",
  "place_of_origin": "Bình Dương",
  "address": "123 Đường X, Phường Y, TX.Bến Cát, Bình Dương",
  "id_issued_date": "2020-05-01",
  "id_expiry_date": "2035-05-01",
  "verified_at": "2024-01-15T10:30:00Z"
}
```

## Mapping to Applicant vertex

```python
async def upsert_applicant(vneid_profile):
    """Create or update Applicant vertex from VNeID profile."""
    # Encrypt sensitive fields with KMS
    encrypted_nid = await kms_encrypt(vneid_profile['national_id'])

    # Check if exists
    existing = await gdb.query("""
        g.V().hasLabel('Applicant').has('vneid_subject', $sub)
    """, sub=vneid_profile['vneid_subject'])

    if existing:
        # Update
        return existing['id']

    # Create new
    applicant_id = await gdb.query("""
        g.addV('Applicant')
         .property('vneid_subject', $sub)
         .property('type', 'citizen')
         .property('national_id_encrypted', $nid)
         .property('display_name_masked', $dn)
         .property('vneid_verified_at', $ts)
         .id()
    """,
        sub=vneid_profile['vneid_subject'],
        nid=encrypted_nid,
        dn=mask_name(vneid_profile['full_name']),
        ts=now()
    )

    return applicant_id
```

### Masking names

```python
def mask_name(full_name):
    """Nguyễn Văn Minh → N*** Văn M***"""
    parts = full_name.split()
    if len(parts) < 2:
        return full_name[0] + '***'
    first = parts[0][0] + '***'
    last = parts[-1][0] + '***'
    middle = ' '.join(parts[1:-1])
    return f"{first} {middle} {last}".strip()
```

## Data pre-fill for TTHC forms

When citizen submits a new TTHC, auto-fill from VNeID profile:

```typescript
// Citizen Portal — Submit wizard
const [formData, setFormData] = useState({});

useEffect(() => {
  // Auto-fill from VNeID on mount
  const profile = session.vneid_profile;
  setFormData({
    applicant_full_name: profile.full_name,
    applicant_id_number: profile.national_id,
    applicant_dob: profile.date_of_birth,
    applicant_address: profile.address,
    applicant_gender: profile.gender,
  });
}, []);
```

Citizen reviews pre-filled data + fills TTHC-specific fields (e.g., for CPXD: công trình detail, địa điểm xây dựng).

## Signature verification

VNeID can also provide digital signature for submitted documents:

```python
async def verify_citizen_signature(document_blob, signature):
    """Verify that a document was signed by the authenticated citizen."""
    return await vneid_verify_signature(
        document=document_blob,
        signature=signature,
        vneid_subject=current_user.vneid_subject
    )
```

This meets NĐ 45/2020 requirement for electronic documents having the same legal validity as paper.

## Privacy considerations

### Data minimization
- Only request scopes needed (`profile`, `id_card`, `address`)
- Do NOT store raw national_id — encrypt via KMS
- Display name masked: `N*** Văn M***`
- Full name only visible to authorized agents/users

### Purpose limitation
- VNeID data only for current TTHC case
- Citizen consent captured explicitly
- Data not shared beyond case scope

### Retention
- Applicant vertex retained for case lifetime
- After case closed + retention period, PII redacted
- Full Applicant deleted after 10 years (per Luật Lưu trữ)

## Hackathon demo strategy

**Real VNeID integration requires:**
- Registration with Bộ Công an as service provider
- Approval process
- Production credentials
- This is NOT feasible for hackathon

**Demo strategy:**
- **Mock VNeID login** — button says "Đăng nhập VNeID (simulated)"
- **Fake VNeID callback** — returns a pre-configured test profile
- **Show the architecture slide** — real VNeID would plug here
- **Talking point:** "Production would integrate với VNeID OAuth theo Đề án 06"

This preserves the narrative without requiring actual integration.

## Links

- VNeID official: https://vneid.gov.vn
- Đề án 06 decision: https://vanban.chinhphu.vn
- Luật Giao dịch điện tử 2005 + sửa đổi
- NĐ 45/2020 về TTHC điện tử
- API docs (for service providers): https://api.vneid.gov.vn/docs

## Pitch talking point

> "Citizen Portal tích hợp VNeID theo Đề án 06 — công dân đăng nhập bằng app định danh quốc gia của Bộ Công an, GovFlow nhận thông tin đã được xác thực, auto-fill form, và khi cần chữ ký số thì ký qua VNeID theo Luật GDĐT 2005 + NĐ 45/2020. Đây là political alignment với chương trình quốc gia, và cũng là UX tối ưu cho công dân — không cần tạo tài khoản riêng."
