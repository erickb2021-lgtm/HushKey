# Setting up emails: welcome codes, sign-in codes, and password recovery (about 20 minutes, free)

HushKey uses **Supabase** (a free online service) to email 6-digit codes and keep each vault's recovery secret. You do this setup **once**. Everyone who downloads your app then gets:

- a **welcome email** with their code when they sign up,
- a **sign-in code** when they sign in on a computer that isn't remembered,
- a **forgot-password code** if they forget their master password.

> Until you finish this, HushKey still works. It just warns that email recovery isn't set up.

Supabase's website changes its menu names now and then. If a button isn't exactly where described, look for the closest match.

---

## 1. Create a Supabase project

1. Go to **[supabase.com](https://supabase.com)** → **Start your project** → sign in with GitHub.
2. Click **New project**:
   - **Name:** `hushkey`
   - **Database password:** click *Generate a password* and save it somewhere safe (HushKey doesn't need it, but Supabase might ask later).
   - **Region:** pick the one closest to you (e.g. *Central US* or *East US*).
3. Click **Create new project** and wait a minute or two until it's ready.

## 2. Create the recovery table and its security rules

1. In the left sidebar, open **SQL Editor** → **New query**.
2. Open `supabase/setup.sql` from this project, copy **everything**, and paste it in.
3. Click **Run**. You should see *Success. No rows returned.*

These rules make sure each person can only ever read their **own** recovery secret, and only after entering a correct email code.

## 3. Make the emails show a 6-digit code

By default Supabase emails a clickable link. HushKey needs a **6-digit code** instead. `{{ .Token }}` is where Supabase puts the code. It makes a new random 6-digit code every time, each code works only once, and it only works for the email it was sent to. Typing any other numbers is refused.

1. Go to **Authentication** → **Emails** (sometimes called *Email Templates*).
2. Open the **Confirm signup** template. This is the **welcome email** new users get. Replace it with:
   - **Subject:** `Welcome to HushKey`
   - **Body:**
     ```html
     <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;background:#0E1116;color:#EEF1F6;border-radius:16px">
       <h1 style="margin:0 0 8px"><span style="color:#3DDC97">Hush</span><span style="color:#F2C14E">Key</span></h1>
       <p style="font-size:16px">Thank you for signing up, and here is your login code:</p>
       <p style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#3DDC97;margin:16px 0">{{ .Token }}</p>
       <p style="color:#A2AAB8;font-size:13px">Type this code into HushKey. It expires in 10 minutes and only works once. If you didn't sign up, you can ignore this email.</p>
     </div>
     ```
   - Click **Save**.
3. Open the **Magic Link** template. This one is used for **sign-in codes** and **forgot-password codes**. Replace it with:
   - **Subject:** `Your HushKey code`
   - **Body:**
     ```html
     <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;padding:24px;background:#0E1116;color:#EEF1F6;border-radius:16px">
       <h1 style="margin:0 0 8px"><span style="color:#3DDC97">Hush</span><span style="color:#F2C14E">Key</span></h1>
       <p style="font-size:16px">Here is your HushKey code:</p>
       <p style="font-size:36px;font-weight:bold;letter-spacing:8px;color:#3DDC97;margin:16px 0">{{ .Token }}</p>
       <p style="color:#A2AAB8;font-size:13px">It expires in 10 minutes and only works once. If you didn't ask for this, someone may know your email. They still can't get into your vault without your computer.</p>
     </div>
     ```
   - Click **Save**.

## 4. Set the code to expire after 10 minutes

1. Go to **Authentication** → **Sign In / Providers** → **Email**.
2. Make sure **Email** is turned **on**.
3. Set **Email OTP Expiration** to `600` (seconds) and **Email OTP Length** to `6`.
4. Click **Save**.

## 5. Let Supabase send emails to everyone (important)

Supabase's built-in email sender is **only for testing**: it sends just a few emails per hour, and only to your own team's email addresses. For anyone else to get codes, connect your own email account. Gmail works and is free.

**Get a Gmail "app password"**
1. Go to your Google Account → **Security** and make sure **2-Step Verification** is on.
2. Search your Google Account settings for **App passwords**, create one named `HushKey`, and copy the 16-letter password.

**Give it to Supabase**
1. In Supabase, go to **Authentication** → **Emails** → **SMTP Settings** and turn on **custom SMTP**.
2. Fill in:
   - **Sender email:** your Gmail address
   - **Sender name:** `HushKey`
   - **Host:** `smtp.gmail.com`
   - **Port:** `587`
   - **Username:** your Gmail address
   - **Password:** the 16-letter app password
3. **Save.**
4. Go to **Authentication** → **Rate Limits** and set emails per hour to something like `30`.

> 🔒 That app password lives **only inside Supabase**. It never goes in HushKey's code or on GitHub, so nobody can pull it out of your app.

## 6. Connect HushKey to your project

1. In Supabase, click **Connect** at the top (or go to **Project Settings** → **API Keys**).
2. Copy the **Project URL** (looks like `https://abcdefghijkl.supabase.co`).
3. Copy the **Publishable key** (starts with `sb_publishable_`). If you only see older keys, use the **anon / public** one.
4. Open `cloud_config.py` in this project and paste them in:
   ```python
   SUPABASE_URL = "https://abcdefghijkl.supabase.co"
   SUPABASE_PUBLIC_KEY = "sb_publishable_xxxxxxxxxxxx"
   ```

> ✅ The publishable key is **meant** to be public and is safe on GitHub. The security rules from step 2 protect the data.
> ⛔ **Never** paste the **secret** key or the **service_role** key anywhere in HushKey. Those skip the security rules.

## 7. Publish

Commit the updated `cloud_config.py` to GitHub and publish a new release (see the README). When you create a vault in the new version, you should get an email with a code.

---

## Good to know

- **Free projects go to sleep** after about a week with no activity. While asleep, codes won't send. Fix: open your Supabase dashboard and click **Restore project**. Each new vault or recovery wakes the clock back up.
- **Gmail limit:** about 500 emails a day, far more than you'll need.
- **What's stored online:** each person's email and a random recovery secret per vault. **Never** their master password, vault file or logins. Even with full access to Supabase, someone still needs that person's computer to get in.
