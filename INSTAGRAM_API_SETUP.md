# Instagram API Setup Guide

Complete guide to enable Instagram post scheduling with Agent 6.

## Prerequisites

✅ Instagram Business or Creator account
✅ Facebook Page connected to your Instagram account
✅ Facebook Developer account

---

## Step 1: Connect Instagram to Facebook Page

1. Go to your Instagram app → Settings → Account
2. Tap "Switch to Professional Account"
3. Choose "Business" or "Creator"
4. In Facebook, go to your Page → Settings → Instagram
5. Click "Connect Account" and log in to Instagram

---

## Step 2: Create Facebook App

1. Go to [Facebook Developers](https://developers.facebook.com/apps/)
2. Click "Create App"
3. Choose "Business" as app type
4. Fill in app details:
   - App Name: "Signal Sanctuary Social Pipeline" (or your choice)
   - Contact Email: your email
5. Click "Create App"

---

## Step 3: Add Instagram Graph API

1. In your app dashboard, click "Add Product"
2. Find "Instagram Graph API" and click "Set Up"
3. Go to Instagram Graph API → Settings
4. Add these permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`

---

## Step 4: Get Instagram Business Account ID

### Option A: Graph API Explorer

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app from dropdown
3. Click "Get User Access Token"
4. Check permissions: `pages_show_list`, `instagram_basic`
5. Run this query:
   ```
   me/accounts?fields=instagram_business_account
   ```
6. Copy the `instagram_business_account.id` value

### Option B: Using curl

```bash
# First get your Page ID
curl -X GET "https://graph.facebook.com/v18.0/me/accounts?access_token=YOUR_ACCESS_TOKEN"

# Then get Instagram Business Account ID
curl -X GET "https://graph.facebook.com/v18.0/PAGE_ID?fields=instagram_business_account&access_token=YOUR_ACCESS_TOKEN"
```

---

## Step 5: Generate Long-Lived Access Token

Short-lived tokens expire in 1 hour. You need a long-lived token (60 days).

### Get User Access Token (short-lived):

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your app
3. Click "Get User Access Token"
4. Select permissions:
   - `instagram_basic`
   - `instagram_content_publish`
   - `pages_read_engagement`
   - `pages_show_list`
5. Click "Generate Access Token"
6. Copy the token (starts with `EAAG...`)

### Exchange for Long-Lived Token:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token?\
grant_type=fb_exchange_token&\
client_id=YOUR_APP_ID&\
client_secret=YOUR_APP_SECRET&\
fb_exchange_token=YOUR_SHORT_LIVED_TOKEN"
```

Response:
```json
{
  "access_token": "EAAG...long token...",
  "token_type": "bearer",
  "expires_in": 5184000  // 60 days
}
```

Copy this long-lived token!

---

## Step 6: Set Up Image Hosting

Instagram API requires publicly accessible image URLs. Choose one:

### Option A: AWS S3 (Recommended)

```bash
# Install AWS CLI
brew install awscli  # macOS
# or: pip install awscli

# Configure
aws configure

# Create bucket
aws s3 mb s3://your-instagram-images

# Make bucket public (or use signed URLs)
aws s3api put-bucket-policy --bucket your-instagram-images --policy file://policy.json
```

`policy.json`:
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "PublicReadGetObject",
    "Effect": "Allow",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::your-instagram-images/*"
  }]
}
```

### Option B: Cloudinary (Easy)

1. Sign up at [Cloudinary](https://cloudinary.com)
2. Get your cloud name from dashboard
3. Upload images via API or web interface

### Option C: Imgur (Simple)

1. Register at [Imgur](https://imgur.com/register)
2. Create app: https://api.imgur.com/oauth2/addclient
3. Use their upload API

---

## Step 7: Configure .env

Add these to your `.env` file:

```bash
# Instagram Business Account ID (from Step 4)
INSTAGRAM_BUSINESS_ACCOUNT_ID=17841405309211844

# Long-Lived Access Token (from Step 5)
INSTAGRAM_ACCESS_TOKEN=EAAGm2ZB...

# Public URL where images are hosted
IMAGE_HOST_BASE_URL=https://your-bucket.s3.amazonaws.com/instagram/

# Schedule posts X days in advance (default: 7)
INSTAGRAM_SCHEDULE_DAYS_AHEAD=7
```

---

## Step 8: Update Image Upload Script

Create `scripts/upload_images_to_host.py`:

```python
"""Upload images to S3/Cloudinary before scheduling posts."""
import boto3
from pathlib import Path

s3 = boto3.client('s3')
BUCKET = 'your-instagram-images'

def upload_images():
    images_dir = Path('images')
    for image in images_dir.glob('*-final.png'):
        print(f"Uploading {image.name}...")
        s3.upload_file(
            str(image),
            BUCKET,
            f'instagram/{image.name}',
            ExtraArgs={'ACL': 'public-read'}
        )
        print(f"  ✓ https://{BUCKET}.s3.amazonaws.com/instagram/{image.name}")

if __name__ == "__main__":
    upload_images()
```

---

## Step 9: Test Connection

```bash
# Test if credentials work
curl -X GET "https://graph.facebook.com/v18.0/INSTAGRAM_BUSINESS_ACCOUNT_ID?\
fields=id,username&\
access_token=YOUR_ACCESS_TOKEN"
```

Expected response:
```json
{
  "id": "17841405309211844",
  "username": "signalsanctuary.health"
}
```

---

## Step 10: Run Agent 6

```bash
# Upload images first
python scripts/upload_images_to_host.py

# Schedule posts
python src/agent_6_instagram_integration.py
```

Posts will be scheduled 7 days ahead (configurable) for review.

---

## Manage Scheduled Posts

View and manage scheduled posts:
- Go to [Meta Business Suite Creator Studio](https://business.facebook.com/creatorstudio)
- Click "Instagram" → "Content Library"
- Filter by "Scheduled"
- Edit or delete as needed

---

## Troubleshooting

### "Invalid OAuth 2.0 Access Token"
- Token expired (regenerate long-lived token)
- Wrong permissions (re-authorize with correct permissions)

### "The image_url provided is not valid"
- Image not publicly accessible
- URL contains invalid characters
- Image exceeds 8MB limit

### "This request requires an upload phase"
- Use `image_url` parameter, not file upload
- Instagram doesn't support direct file upload via API

### "Scheduling is not available"
- Account may need verification
- Can only schedule 10 min to 75 days ahead
- Business account required (not personal)

---

## Security Notes

⚠️ **Never commit access tokens to git**
✅ Use `.env` file (already in `.gitignore`)
✅ Rotate tokens every 60 days
✅ Use environment variables in production
✅ Restrict app permissions to minimum needed

---

## Rate Limits

- 200 calls per hour per user
- 4800 calls per day per app
- Be respectful of API limits

---

## Cost Estimate

- **Instagram API**: Free
- **AWS S3**: ~$0.023/GB storage + $0.09/GB transfer
- **Cloudinary**: Free tier: 25GB storage, 25GB bandwidth/month
- **Imgur**: Free for non-commercial use

For 5 images (~5MB total): **< $0.01/month**

---

## Support

- [Instagram Graph API Docs](https://developers.facebook.com/docs/instagram-api)
- [Content Publishing Guide](https://developers.facebook.com/docs/instagram-api/guides/content-publishing)
- [Meta Business Help](https://www.facebook.com/business/help)
