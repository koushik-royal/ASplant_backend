import os
import shutil
import time
from typing import Optional, BinaryIO
from config import settings

# Cloudinary configuration
CLOUDINARY_AVAILABLE = False
try:
    import cloudinary
    import cloudinary.uploader
    from urllib.parse import urlparse

    cloud_name = settings.CLOUDINARY_CLOUD_NAME or os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = settings.CLOUDINARY_API_KEY or os.getenv("CLOUDINARY_API_KEY")
    api_secret = settings.CLOUDINARY_API_SECRET or os.getenv("CLOUDINARY_API_SECRET")
    cloudinary_url = settings.CLOUDINARY_URL or os.getenv("CLOUDINARY_URL")

    if cloudinary_url:
        os.environ["CLOUDINARY_URL"] = cloudinary_url
        parsed = urlparse(cloudinary_url)
        c_name = parsed.hostname
        c_key = parsed.username
        c_secret = parsed.password
        cloudinary.config(
            cloud_name=c_name,
            api_key=c_key,
            api_secret=c_secret,
            secure=True
        )
    elif cloud_name and api_key and api_secret:
        cloudinary.config(
            cloud_name=cloud_name,
            api_key=api_key,
            api_secret=api_secret,
            secure=True
        )

    cfg = cloudinary.config()
    if cfg.cloud_name and cfg.api_key and cfg.api_secret:
        CLOUDINARY_AVAILABLE = True
        print(f"[STORAGE] Cloudinary active & configured for cloud '{cfg.cloud_name}'.")
    else:
        CLOUDINARY_AVAILABLE = False
        print("[STORAGE] Cloudinary credentials incomplete or missing; local disk fallback active.")
except Exception as e:
    print(f"[STORAGE] Cloudinary initialization warning: {e}")
    CLOUDINARY_AVAILABLE = False


class StorageService:
    @staticmethod
    def is_cloud_enabled() -> bool:
        return CLOUDINARY_AVAILABLE

    @staticmethod
    def upload_image(file_obj: BinaryIO, filename: str, folder: str = "products") -> str:
        """
        Uploads an image file object to persistent Cloudinary storage if available.
        Falls back safely to local container storage if Cloudinary is not configured.
        Returns a permanent HTTPS URL.
        """
        if CLOUDINARY_AVAILABLE:
            try:
                # Seek to beginning in case stream was partially read
                if hasattr(file_obj, "seek"):
                    file_obj.seek(0)

                base_name = os.path.splitext(filename)[0]
                upload_res = cloudinary.uploader.upload(
                    file_obj,
                    folder=f"plantora/{folder}",
                    public_id=f"{base_name}_{int(time.time())}",
                    resource_type="image",
                    overwrite=True
                )
                secure_url = upload_res.get("secure_url") or upload_res.get("url")
                if secure_url:
                    print(f"[STORAGE] Successfully uploaded to Cloudinary: {secure_url}")
                    return secure_url
            except Exception as cloud_err:
                print(f"[STORAGE] Cloudinary upload failed: {type(cloud_err).__name__} ({cloud_err}); falling back to local disk.")

        # Local filesystem fallback
        local_dir = os.path.join(settings.UPLOAD_DIR, folder)
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)

        if hasattr(file_obj, "seek"):
            file_obj.seek(0)

        with open(local_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        base_url = (settings.SERVER_BASE_URL or "https://asplant-backend-1.onrender.com").rstrip("/")
        local_url = f"{base_url}/{settings.UPLOAD_DIR}/{folder}/{filename}"
        print(f"[STORAGE] Saved locally: {local_url}")
        return local_url

    @staticmethod
    def delete_image(image_url_or_path: str) -> bool:
        """
        Deletes an image from Cloudinary or the local filesystem.
        """
        if not image_url_or_path or not image_url_or_path.strip():
            return False

        clean_path = image_url_or_path.strip()

        # Handle Cloudinary deletion
        if "res.cloudinary.com" in clean_path:
            if CLOUDINARY_AVAILABLE:
                try:
                    # Cloudinary URL format: https://res.cloudinary.com/<cloud>/image/upload/v.../plantora/products/<public_id>.ext
                    parts = clean_path.split("/upload/")
                    if len(parts) > 1:
                        sub_path = parts[1]
                        # Remove version if present (e.g. v1234567890/)
                        if sub_path.startswith("v") and "/" in sub_path:
                            sub_path = sub_path.split("/", 1)[1]
                        public_id = os.path.splitext(sub_path)[0]
                        res = cloudinary.uploader.destroy(public_id)
                        print(f"[STORAGE] Cloudinary delete result for '{public_id}': {res}")
                        return True
                except Exception as del_err:
                    print(f"[STORAGE] Failed to delete from Cloudinary: {del_err}")
            return False

        # Handle local disk deletion
        try:
            if "uploads/" in clean_path:
                rel_path = clean_path.split("uploads/")[-1]
                local_file = os.path.join(settings.UPLOAD_DIR, rel_path)
                if os.path.exists(local_file):
                    os.remove(local_file)
                    print(f"[STORAGE] Removed local file: {local_file}")
                    return True
        except Exception as local_del_err:
            print(f"[STORAGE] Failed to delete local file: {local_del_err}")

        return False


storage_service = StorageService()
