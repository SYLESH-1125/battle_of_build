require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const demoConfig = require('../demouser.json');

const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SECRET_KEY;

if (!supabaseUrl || !supabaseServiceKey) {
  console.error('❌ Missing SUPABASE_URL or SUPABASE_SECRET_KEY in environment');
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseServiceKey);

const demoUserConfigs = [
  { email: demoConfig.demo_users[0], role: 'doctor' },
  { email: demoConfig.demo_users[1], role: 'admin' },
  { email: demoConfig.demo_users[2], role: 'patient' },
];

const hiddenPassword = demoConfig.hidden_password_prefix + demoConfig.demo_pin;

async function setupDemoUsers() {
  console.log('🔐 DEMO MODE USER PROVISIONING');
  console.log('================================');
  console.log(`📧 Demo PIN: ${demoConfig.demo_pin}`);
  console.log(`🔑 Hidden Password: ${hiddenPassword}`);
  console.log('');

  for (const config of demoUserConfigs) {
    try {
      console.log(`⏳ Creating demo user: ${config.email} (role: ${config.role})`);

      // Create user with hidden password
      const { data: authData, error: authError } = await supabase.auth.admin.createUser({
        email: config.email,
        password: hiddenPassword,
        email_confirm: true,
      });

      let userId;
      if (authError) {
        console.error(`   ❌ Auth Error: ${authError.message}`);
        // Try to find existing user by email and use that id
        const { data: listData, error: listError } = await supabase.auth.admin.listUsers();
        if (listError) {
          console.error(`   ❌ Could not list users: ${listError.message}`);
          continue;
        }
        const existing = listData?.users.find(u => u.email === config.email);
        if (!existing) {
          console.error(`   ❌ User ${config.email} not found after create failure`);
          continue;
        }
        userId = existing.id;
        console.log(`   ℹ️ Using existing user id: ${userId}`);
      } else {
        userId = authData.user.id;
        console.log(`   ✅ User created: ${userId}`);
      }

      // Assign role
      const { error: roleError } = await supabase
        .from('user_roles')
        .upsert(
          {
            user_id: userId,
            role: config.role,
          },
          { onConflict: 'user_id' }
        );

      if (roleError) {
        console.error(`   ❌ Role Error: ${roleError.message}`);
        continue;
      }

      console.log(`   ✅ Role assigned: ${config.role}`);
      console.log(`   📊 Demo user ready for login`);
      console.log('');
    } catch (err) {
      console.error(`❌ Unexpected error for ${config.email}:`, err.message);
    }
  }

  console.log('✅ Demo user provisioning complete!');
  console.log('');
  console.log('🎭 DEMO MODE ACTIVATED');
  console.log('Users can now login with PIN: 123456');
  process.exit(0);
}

setupDemoUsers();
