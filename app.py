def call_kaggle_svd(image_path, out_path, server_url):
    try:
        client = Client(server_url)
        res = client.predict(
            image=handle_file(image_path),
            motion_bucket_id=127,
            api_name="/predict"
        )
        
        # अगर रिजल्ट dict/object के रूप में आए तो पाथ निकालें
        actual_path = None
        if isinstance(res, str):
            actual_path = res
        elif isinstance(res, dict):
            actual_path = res.get("video") or res.get("path") or res.get("value")
        elif isinstance(res, (list, tuple)) and len(res) > 0:
            actual_path = res[0]
            if isinstance(actual_path, dict):
                actual_path = actual_path.get("video") or actual_path.get("path")
                
        if actual_path and os.path.exists(actual_path):
            import shutil
            shutil.copy(actual_path, out_path)
            return True
        else:
            print(f"Kaggle response format not recognized: {res}")
    except Exception as e:
        st.write(f"⚠️ Kaggle Engine Error: {e}")
    return False
