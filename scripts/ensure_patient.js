require('dotenv').config();
const { createClient } = require('@supabase/supabase-js');

const supabaseUrl = process.env.SUPABASE_URL;
const supabaseServiceKey = process.env.SUPABASE_SECRET_KEY;
const supabase = createClient(supabaseUrl, supabaseServiceKey);

async function ensurePatientPassword() {
  const { data: allUsers } = await supabase.auth.admin.listUsers();
  
  console.log('🔧 ENSURING PATIENT USER PASSWORD');
  console.log('================================');
  
  const patientUser = allUsers?.users.find(u => u.email === 'demopatient@hospital.com');
  
  if (!patientUser) {
    console.log('❌ Patient user not found. Creating...');
    
    // Create patient user
    const { data: newUser, error: createError } = await supabase.auth.admin.createUser({
      email: 'demopatient@hospital.com',
      password: 'vault-demo-123456',
      email_confirm: true,
    });
    
    if (createError) {
      console.error('❌ Error creating user:', createError.message);
      process.exit(1);
    }
    
    console.log('✅ Patient user created:', newUser.user.id);
    
    // Set role
    const { error: roleError } = await supabase
      .from('user_roles')
      .upsert(
        {
          user_id: newUser.user.id,
          role: 'patient',
        },
        { onConflict: 'user_id' }
      );
    
    if (roleError) {
      console.error('❌ Error setting role:', roleError.message);
    } else {
      console.log('✅ Patient role assigned');
    }
  } else {
    console.log('✅ Patient user found:', patientUser.id);
    
    // Update password
    const { error: updateError } = await supabase.auth.admin.updateUserById(
      patientUser.id,
      { password: 'vault-demo-123456' }
    );
    
    if (updateError) {
      console.error('❌ Error updating password:', updateError.message);
    } else {
      console.log('✅ Password set successfully');
    }
  }
  
  process.exit(0);
}

ensurePatientPassword();
