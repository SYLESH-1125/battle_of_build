#!/usr/bin/env node

/**
 * Autonomous User Provisioning Script
 * Creates Doctor, Admin, and Patient test users via Supabase Admin API
 */

const { createClient } = require("@supabase/supabase-js");

const SUPABASE_URL = "https://cdgcmcznmqykmzyovnmn.supabase.co";
const SUPABASE_SERVICE_ROLE_KEY =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E";

const testUsers = [
  {
    email: "doctor@hospital.com",
    password: "TempPassword123!@#",
    role: "doctor",
    metadata: { role: "doctor" },
  },
  {
    email: "admin@hospital.com",
    password: "TempPassword123!@#",
    role: "admin",
    metadata: { role: "admin" },
  },
  {
    email: "patient@hospital.com",
    password: "TempPassword123!@#",
    role: "patient",
    metadata: { role: "patient" },
  },
];

async function provisionUsers() {
  try {
    console.log("🔐 Initializing Supabase Admin Client...");
    const supabase = createClient(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, {
      auth: {
        autoRefreshToken: false,
        persistSession: false,
      },
    });

    console.log("📝 Creating test users...\n");

    for (const user of testUsers) {
      try {
        console.log(`Creating user: ${user.email} (role: ${user.role})`);

        const { data, error } = await supabase.auth.admin.createUser({
          email: user.email,
          password: user.password,
          email_confirm: true,
          user_metadata: user.metadata,
        });

        if (error) {
          throw error;
        }

        console.log(`✅ Created user: ${user.email}`);
        console.log(`   User ID: ${data.user.id}\n`);
      } catch (err) {
        console.error(`❌ Error creating ${user.email}:`, err.message);
      }
    }

    // Verify users were created and user_roles were auto-provisioned
    console.log("\n📊 Verifying user_roles table...");
    const { data: rolesData, error: rolesError } = await supabase
      .from("user_roles")
      .select("id, user_id, role, created_at");

    if (rolesError) {
      throw rolesError;
    }

    console.log(`✅ Found ${rolesData.length} entries in user_roles table:`);
    rolesData.forEach((entry) => {
      console.log(`   - ${entry.role} (user_id: ${entry.user_id})`);
    });

    console.log("\n✨ User provisioning complete!");
    process.exit(0);
  } catch (error) {
    console.error("❌ Fatal error:", error);
    process.exit(1);
  }
}

provisionUsers();
