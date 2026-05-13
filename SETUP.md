# JIS Tennis Booking — Setup Guide

After setup your computer never needs to be on for bookings to happen.

---

## Step 1 — Create a GitHub account

Go to **github.com** and sign up for a free account if you don't have one.

---

## Step 2 — Create a private repository

1. Click the **+** button (top right) → **New repository**
2. Name it: `tennis-booking`
3. Set it to **Private**
4. Leave everything else as default
5. Click **Create repository**

---

## Step 3 — Upload the files

1. In your new repo, click **Add file** → **Upload files**
2. Drag and drop ALL files from the `~/tennis-booking/` folder on your Mac:
   - `book.py`
   - `requirements.txt`
   - `schedule.json`
   - The `.github` folder (whole folder)
   - The `docs` folder (whole folder)
3. Click **Commit changes**

---

## Step 4 — Add your email as a secret

1. In your repo, click **Settings** (top menu)
2. Left sidebar → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Name: `BOOKING_EMAIL`
5. Value: `hanchoo@gmail.com`
6. Click **Add secret**

---

## Step 5 — Enable GitHub Pages (your booking website)

1. Still in **Settings**, click **Pages** in the left sidebar
2. Under "Source", select **Deploy from a branch**
3. Branch: **main** — Folder: **/docs**
4. Click **Save**
5. Wait 1–2 minutes, then your site will appear at:
   `https://YOUR-USERNAME.github.io/tennis-booking/`

---

## Step 6 — Create a Personal Access Token

This lets the website save your bookings to GitHub.

1. Click your profile photo (top right) → **Settings**
2. Scroll all the way down → **Developer settings** (left sidebar)
3. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
4. Name it anything (e.g. "Tennis Booking")
5. Expiration: **No expiration**
6. Under **Repository access** → select **Only select repositories** → pick `tennis-booking`
7. Under **Permissions** → **Repository permissions**:
   - Set **Contents** to **Read and write**
   - Set **Actions** to **Read and write**
8. Click **Generate token**
9. **Copy the token now** — you won't see it again

---

## Step 7 — Open your booking site

1. Go to `https://YOUR-USERNAME.github.io/tennis-booking/`
2. Enter your GitHub username, repository name (`tennis-booking`), and the token you just copied
3. Click **Save & Continue**

That's it! You'll never need to do this again.

---

## Daily use

1. Open `https://YOUR-USERNAME.github.io/tennis-booking/` from any device
2. Click **Select** on the courts and times you want
3. Click **Schedule All Bookings**
4. Close the page

GitHub runs the bookings automatically at **00:00** on the correct day.
No computer or server needed.
