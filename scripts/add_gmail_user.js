#!/usr/bin/env node

const { createClient } = require("@supabase/supabase-js");

const SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co";
const SUPABASE_SERVICE_ROLE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E";

async function addTestUser() {
  try {
    console.log("🔐 Adding your Gmail test user...");
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
      auth: { autoRefreshToken: false, persistSession: false },
    });

    const { data, error } = await supabase.auth.admin.createUser({
      email: "sanjaysmpmuruga02@gmail.com",
      password: "TempPassword123!@#",
      email_confirm: true,
      user_metadata: { role: "patient" },
    });

    if (error) throw error;

    console.log(`✅ Created user: sanjaysmpmuruga02@gmail.com`);
    console.log(`   User ID: ${data.user.id}`);
    process.exit(0);
  } catch (error) {
    console.error("❌ Error:", error.message);
    process.exit(1);
  }
}

addTestUser();
