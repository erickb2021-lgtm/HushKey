"""
Email settings for HushKey (Supabase). See SETUP_EMAIL_RECOVERY.md.

Is it safe to put these in a public GitHub repo? Yes. This is Supabase's
"publishable" key, made to be shipped inside apps. It can't read anyone's
data by itself: the database rules in supabase/setup.sql only let a person
read their own recovery secret, and only after they've proven they own their
email with a code.

NEVER put the "secret" / "service_role" key here. That one bypasses the rules.
"""

SUPABASE_URL = "https://kmeccpycoakefmmcnztr.supabase.co"
SUPABASE_PUBLIC_KEY = "sb_publishable_uFM_I_R9f2NMfr4cnh9yKw_OnoBjwKV"
