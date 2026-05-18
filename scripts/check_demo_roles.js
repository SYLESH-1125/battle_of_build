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

async function main() {
  try {
    const { data: listData, error: listError } = await supabase.auth.admin.listUsers();
    if (listError) {
      console.error('❌ Could not list users:', listError.message);
      process.exit(1);
    }

    for (const email of demoConfig.demo_users) {
      const user = listData?.users.find(u => u.email === email);
      const userId = user?.id ?? null;

      let role = null;
      if (userId) {
        const { data: roleData, error: roleError } = await supabase
          .from('user_roles')
          .select('role')
          .eq('user_id', userId)
          .maybeSingle();

        if (roleError) {
          console.error(`   ❌ Role query error for ${email}:`, roleError.message);
        } else {
          role = roleData?.role ?? null;
        }
      }

      console.log(`${email} -> userId: ${userId}, role: ${role}`);
    }
  } catch (err) {
    console.error('❌ Unexpected error:', err instanceof Error ? err.message : String(err));
  }

  process.exit(0);
}

main();
