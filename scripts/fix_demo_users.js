require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.SUPABASE_URL || process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SECRET_KEY;

const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function fixDemoUsers() {
  console.log('🔧 FIXING DEMO USER ROLES');
  console.log('================================');

  try {
    // 1. Delete the demodoctor@hospital.com user (incorrect creation)
    console.log('⏳ Removing incorrect user: demodoctor@hospital.com');
    const { data: allUsers } = await supabase.auth.admin.listUsers();
    const demoDoctoUser = allUsers?.users.find(u => u.email === 'demodoctor@hospital.com');
    
    if (demoDoctoUser) {
      await supabase.auth.admin.deleteUser(demoDoctoUser.id);
      console.log('   ✅ Removed demodoctor@hospital.com');
    }

    // 2. Update sanjaysmpmuruga02@gmail.com role to doctor
    console.log('⏳ Updating sanjaysmpmuruga02@gmail.com to doctor role');
    const { data: response } = await supabase
      .from('user_roles')
      .select('user_id')
      .eq('user_id', (await supabase.auth.admin.listUsers()).data.users.find(u => u.email === 'sanjaysmpmuruga02@gmail.com')?.id)
      .single();

    const gmailUser = allUsers?.users.find(u => u.email === 'sanjaysmpmuruga02@gmail.com');
    if (gmailUser) {
      await supabase
        .from('user_roles')
        .upsert(
          {
            user_id: gmailUser.id,
            role: 'doctor',
          },
          { onConflict: 'user_id' }
        );
      console.log('   ✅ Updated to doctor role');
    }

    // 3. Update demoadmin@hospital.com role to admin (it was set to patient)
    console.log('⏳ Updating demoadmin@hospital.com to admin role');
    const demoAdminUser = allUsers?.users.find(u => u.email === 'demoadmin@hospital.com');
    if (demoAdminUser) {
      await supabase
        .from('user_roles')
        .upsert(
          {
            user_id: demoAdminUser.id,
            role: 'admin',
          },
          { onConflict: 'user_id' }
        );
      console.log('   ✅ Updated to admin role');
    }

    console.log('');
    console.log('✅ Demo user roles corrected!');
    
  } catch (err) {
    console.error('❌ Error:', err.message);
  }

  process.exit(0);
}

fixDemoUsers();
