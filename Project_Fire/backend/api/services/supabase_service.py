import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment from a fixed location relative to this script
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(BASE_DIR, '.env')
load_dotenv(env_path)

class SupabaseService:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_ANON_KEY")
        self.bucket_name = os.getenv("SUPABASE_BUCKET_NAME", "detections")
        
        if self.url and self.key:
            self.supabase: Client = create_client(self.url, self.key)
        else:
            self.supabase = None
            print("⚠️ Supabase credentials missing. Image uploads will fail.")

    async def upload_image(self, file_path: str, destination_path: str) -> str:
        """
        Uploads a local file to Supabase Storage and returns the public URL.
        """
        if not self.supabase:
            print("❌ Supabase client unavailable. Evidence photo skipped.")
            return ""

        try:
            with open(file_path, 'rb') as f:
                # Attempt the restricted cloud deposit
                print(f"🛰️ Syncing evidence to vault: {destination_path}...")
                self.supabase.storage.from_(self.bucket_name).upload(
                    path=destination_path,
                    file=f,
                    file_options={"content-type": "image/jpeg"}
                )
                
                # Retrieve the public access link
                public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(destination_path)
                print(f"✅ Evidence secured. Cloud URL: {public_url}")
                return public_url
        except Exception as e:
            error_msg = str(e)
            if "403" in error_msg or "RLS" in error_msg:
                print(f"⚠️ CLOUD ACCESS DENIED (RLS): Your Supabase bucket '{self.bucket_name}' has security locks on.")
                print("💡 TO FIX: Run the SQL Script shared in the chat to unlock 'detections' bucket.")
            else:
                print(f"❌ Storage Failure: {error_msg}")
            return ""

supabase_service = SupabaseService()
