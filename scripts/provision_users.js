#!/usr/bin/env node
/**
 * Autonomous User Provisioning Script
 * Creates test users: Doctor, Admin, Patient
 * Uses Supabase Admin Auth API
 */

const { createClient } = require('@supabase/supabase-js');

const SUPABASE_URL = 'https://cdgcmcznmqykmzyovnmn.supabase.co';
const SUPABASE_SECRET_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNkZ2NtY3pubXF5a216eW92bm1uIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3ODkzMzU1NywiZXhwIjoyMDk0NTA5NTU3fQ.ASi5cGTF-UXHJDnmJe41fSGhdBUTClYd4gDyiqkah5E';

const admin = createClient(SUPABASE_URL, SUPABASE_SECRET_KEY);

const TEST_USERS = [
  {
    email: 'doctor@hospital.com',
    password: 'TestPassword123!@#',
    metadata: { role: 'doctor' },
    name: 'Doctor'
  },
  {
    email: 'admin@hospital.com',
    password: 'TestPassword123!@#',
    metadata: { role: 'admin' },
    name: 'Admin'
  },
  {
    email: 'patient@hospital.com',
    password: 'TestPassword123!@#',
    metadata: { role: 'patient' },
    name: 'Patient'
  }
];

async function provisionUsers() {
  console.log('🚀 Starting autonomous user provisioning...\n');

  for (const user of TEST_USERS) {
    try {
      const { data, error } = await admin.auth.admin.createUser({
        email: user.email,
        password: user.password,
        user_metadata: user.metadata,
        email_confirm: true // Skip email verification for testing
      });

      if (error) {
        if (error.message.includes('already exists')) {
          console.log(`⚠️  ${user.name} (${user.email}) already exists - skipping`);
        } else {
          throw error;
        }
      } else {
        console.log(`✅ Created ${user.name}: ${user.email}`);
        console.log(`   ├─ ID: ${data.user.id}`);
        console.log(`   ├─ Role: ${user.metadata.role}`);
        console.log(`   └─ Confirmed: ${data.user.email_confirmed_at ? 'Yes' : 'No'}\n`);
      }
    } catch (err) {
      console.error(`❌ Error creating ${user.name}:`, err.message);
    }
  }

  console.log('✅ User provisioning complete!');
  console.log('\n📊 Verifying user_roles table...');

  // Verify user_roles were created by trigger
  try {
    const { data: roles, error: rolesError } = await admin
      .from('user_roles')
      .select('user_id, role');

    if (rolesError) throw rolesError;

    console.log(`✅ Found ${roles.length} entries in user_roles table:`);
    roles.forEach(role => {
      console.log(`   ├─ ${role.role.toUpperCase()}: ${role.user_id.substring(0, 8)}...`);
    });
  } catch (err) {
    console.error('❌ Error verifying user_roles:', err.message);
  }

  console.log('\n🎯 Ready for testing!');
}

provisionUsers().catch(console.error);
