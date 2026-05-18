require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');
const demoConfig = require('../demouser.json');

const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SECRET_KEY;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

const demoUserConfigs = [
  { email: demoConfig.demo_users[0], role: 'doctor' },
  { email: demoConfig.demo_users[1], role: 'admin' },
  { email: demoConfig.demo_users[2], role: 'patient' },
];

const demoPassword = demoConfig.hidden_password_prefix + demoConfig.demo_pin;

async function setDemoPasswords() {
  console.log('🔑 SETTING DEMO USER PASSWORDS');
  console.log('================================');
  console.log(`🔐 Password: ${demoPassword}`);
  console.log('');

  for (const config of demoUserConfigs) {
    try {
      console.log(`⏳ Setting password for: ${config.email}`);

      // Update user password
      const { data, error } = await supabase.auth.admin.updateUserById(
        (await supabase.auth.admin.listUsers()).data.users.find(u => u.email === config.email)?.id,
        { password: demoPassword }
      );

      if (error) {
        console.error(`   ❌ Error: ${error.message}`);
        continue;
      }

      console.log(`   ✅ Password set successfully`);
      console.log('');
    } catch (err) {
      console.error(`❌ Unexpected error for ${config.email}:`, err.message);
    }
  }

  console.log('✅ Password setup complete!');
  process.exit(0);
}

setDemoPasswords();
