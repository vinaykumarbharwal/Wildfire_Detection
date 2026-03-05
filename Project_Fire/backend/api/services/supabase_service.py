import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

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
            raise Exception("Supabase client not initialized")

        with open(file_path, 'rb') as f:
            # Upload the file
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=destination_path,
                file=f,
                file_options={"content-type": "image/jpeg"}
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(destination_path)
            return public_url

supabase_service = SupabaseService()
